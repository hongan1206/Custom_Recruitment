from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging 
_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Các trường điểm
    # cv_score = fields.Float(
    #     string="CV Score",
    #     help="Score calculated from CV analysis (AI, Regex, OCR, etc.)"
    # )
    test_score = fields.Float(
        string="Test Score",
        compute="_compute_test_score",
        store=False,
        help="Score from test results"
    )
    hr_score = fields.Float(
        string="HR Score",
        help="Score manually entered by HR"
    )
    avg_score = fields.Float(
        string="Average Score",
        compute="_compute_avg_score",
        store=False,
        help="Automatically calculated average score"
    )

    matching_score = fields.Float(
        string="Matching Score(%)",
        compute="_compute_matching_score",
        store=False,
        readonly=True,
    )
    #(1)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    required_skill_ids = fields.Many2many(
        'hr.skill','hr_applicant_required_skill_rel',
        'applicant_id','skill_id',
        string='Required Skills', 
        compute='_compute_required_skills_from_job',
        store=True
    )
    #(1)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#     filtered_candidate_skill_ids = fields.One2many(
#     'hr.candidate.skill',
#     compute='_compute_filtered_candidate_skill_ids',
#     string="Filtered Candidate Skills"
# )

#     @api.depends('candidate_skill_ids.skill_id', 'required_skill_ids')
#     def _compute_filtered_candidate_skill_ids(self):
#         for applicant in self:
#             if applicant.required_skill_ids:
#                 applicant.filtered_candidate_skill_ids = applicant.candidate_skill_ids.filtered(
#                     lambda cs: cs.skill_id.id in applicant.required_skill_ids.ids
#                 )
#             else:
#                 applicant.filtered_candidate_skill_ids = False
    #(2)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    @api.depends('job_id.skill_ids') # Phụ thuộc vào job_id và danh sách skill của job
    def _compute_required_skills_from_job(self):
        for applicant in self:
            if applicant.job_id and applicant.job_id.skill_ids:
                applicant.required_skill_ids = [(6, 0, applicant.job_id.skill_ids.ids)]
            else:
                applicant.required_skill_ids = [(5, 0, 0)] # Xóa tất cả nếu không có job hoặc job không có skill
    #(2)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    #(3)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    @api.constrains('test_score', 'hr_score')
    def _check_score_limits(self):
        for record in self:
            for field_name in ['test_score', 'hr_score']:
                value = getattr(record, field_name)
                if value < 0 or value > 100:
                    raise ValidationError("Yêu cầu nhập lại điểm ")
    #(3)+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    @api.depends('candidate_skill_ids.skill_id', 'candidate_skill_ids.skill_level_id', 'job_id.skill_ids')
    def _compute_matching_score(self):
        for applicant in self:
            job_skill_ids = set(applicant.job_id.skill_ids.ids)
            levels = [
                cs.skill_level_id.level_progress
                for cs in applicant.candidate_skill_ids
                if cs.skill_id and cs.skill_id.id in job_skill_ids and cs.skill_level_id and cs.skill_level_id.level_progress is not None
            ]
            applicant.matching_score = sum(levels) / len(levels) if levels else 0

    @api.depends('test_score', 'hr_score', 'matching_score')
    def _compute_avg_score(self):
        """Tính điểm trung bình từ các nguồn điểm"""
        for record in self:
            scores = [record.test_score, record.hr_score, record.matching_score]
            valid_scores = [score for score in scores if score > 0]  # Chỉ tính các điểm hợp lệ (> 0)
            record.avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

 #Code Mình-------------------------------------------------------------------------

    def update_test_score(self, applicant_id, new_score):
        """Cập nhật điểm bài test cho một ứng viên cụ thể"""
        applicant = self.browse(applicant_id)
        if applicant:
            applicant.test_score = new_score

    def update_hr_score(self, applicant_id, new_score):
        """Cập nhật điểm HR cho một ứng viên cụ thể"""
        applicant = self.browse(applicant_id)
        if applicant:
            applicant.hr_score = new_score

    @api.model_create_multi
    def create(self, vals_list):
        applicants = super().create(vals_list)
        for applicant in applicants:
            applicant._generate_candidate_skills_from_job()
        return applicants

    def write(self, vals):
        res = super().write(vals)
        if 'job_id' in vals:
            for applicant in self:
                applicant._generate_candidate_skills_from_job()
        return res

    def _generate_candidate_skills_from_job(self):
        for applicant in self:
            candidate = applicant.candidate_id
            job = applicant.job_id
            if not (candidate and job and job.skill_ids):
                continue
            for skill in job.skill_ids:
                skill_type = skill.skill_type_id
                default_level = skill_type.skill_level_ids.filtered(lambda s: s.default_level)[:1] or skill_type.skill_level_ids[:1]
                if not self.env['hr.candidate.skill'].search_count([
                    ('candidate_id', '=', candidate.id),
                    ('skill_id', '=', skill.id)
                ]):
                    self.env['hr.candidate.skill'].create({
                        'candidate_id': candidate.id,
                        'skill_id': skill.id,
                        'skill_type_id': skill_type.id,
                        'skill_level_id': default_level.id if default_level else False,
                    })
#Code Mình-------------------------------------------------------------------------                  
#Code Bạn
    # def create(self, vals_list):
    #     _logger.info("HrApplicant create (custom): Original vals_list: %s", vals_list)
    #     processed_vals_list = []
    #     for vals in vals_list:
    #         current_vals = vals.copy()
    #         job_id = current_vals.get('job_id')
    #         if job_id:
    #             job = self.env['hr.job'].browse(job_id)
    #             if job.exists() and job.skill_ids:
    #                 input_skill_commands = current_vals.get('candidate_skill_ids', [])
    #                 skills_in_vals_ids = set()
    #                 for command in input_skill_commands:
    #                     if command[0] == 0 or command[0] == 1:
    #                         if command[2] and 'skill_id' in command[2]:
    #                             skills_in_vals_ids.add(command[2]['skill_id'])
    #                     elif command[0] == 4:
    #                         skills_in_vals_ids.add(command[1])
    #                     elif command[0] == 6:
    #                         skills_in_vals_ids.update(command[2])
                    
    #                 new_skill_lines_from_job = []
    #                 for job_skill in job.skill_ids:
    #                     if job_skill.id not in skills_in_vals_ids:
    #                         skill_type = job_skill.skill_type_id
    #                         default_level = skill_type.skill_level_ids.filtered('default_level')[:1] or \
    #                                         skill_type.skill_level_ids[:1]
    #                         new_skill_lines_from_job.append((0, 0, {
    #                             'skill_id': job_skill.id,
    #                             'skill_type_id': skill_type.id,
    #                             'skill_level_id': default_level.id if default_level else False,
    #                         }))
                    
    #                 if new_skill_lines_from_job:
    #                     current_vals['candidate_skill_ids'] = list(input_skill_commands) + new_skill_lines_from_job
    #                     _logger.info("HrApplicant create (custom): Updated candidate_skill_ids for job_id=%s: %s",
    #                                  job_id, current_vals['candidate_skill_ids'])
    #         processed_vals_list.append(current_vals)

    #     applicants = super(HrApplicant, self).create(processed_vals_list)
    #     _logger.info("HrApplicant create (custom): Created applicants: %s", applicants.ids)
    #     return applicants

    # @api.onchange('job_id')
    # def _onchange_job_id(self):
    #     _logger.info("hr_scoring: _onchange_job_id called for applicant id=%s, job_id=%s", self.id, self.job_id.id if self.job_id else None)
    #     if self.job_id:
    #         existing_skill_ids = {cs.skill_id.id for cs in self.candidate_skill_ids if cs.skill_id}
    #         skill_lines = []
    #         for skill in self.job_id.skill_ids:
    #             if skill.id not in existing_skill_ids:
    #                 default_level = skill.skill_type_id.skill_level_ids.filtered('default_level') or skill.skill_type_id.skill_level_ids[:1]
    #                 skill_lines.append((0, 0, {
    #                     'skill_id': skill.id,
    #                     'skill_type_id': skill.skill_type_id.id,
    #                     'skill_level_id': default_level and default_level.id or False,
    #                 }))
    #         if skill_lines:
    #             self.candidate_skill_ids = [(4, cs.id) for cs in self.candidate_skill_ids] + skill_lines
    #         _logger.info("hr_scoring: candidate_skill_ids updated for job_id=%s", self.job_id.id)

    @api.depends('survey_id')
    def _compute_test_score(self):
        for applicant in self:
            score = 0
            if applicant.survey_id:
                user_input = self.env['survey.user_input'].search([
                    ('survey_id', '=', applicant.survey_id.id),
                    ('state', '=', 'done'),
                    ('applicant_id', '=', applicant.id)
                ], limit=1)
                if user_input:
                    score = user_input.scoring_percentage or 0
            applicant.test_score = score
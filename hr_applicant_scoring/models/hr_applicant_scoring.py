from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    required_skill_ids = fields.Many2many(
        'hr.skill','hr_applicant_required_skill_rel',
        'applicant_id','skill_id',
        string='Required Skills',
        compute='_compute_required_skills_from_job',
        store=True
    )
    test_score = fields.Float(
        string="Form Test Score",
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


#Nhóm 1: 
    @api.depends('job_id.skill_ids') 
    def _compute_required_skills_from_job(self):
        for applicant in self:
            if applicant.job_id and applicant.job_id.skill_ids:
                applicant.required_skill_ids = [(6, 0, applicant.job_id.skill_ids.ids)]
            else:
                applicant.required_skill_ids = [(5, 0, 0)] 
 

#Nhóm 2: Tạo tự động skill cho ứng viên từ job
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


  #Nhóm 3: Làm việc với nhóm điểm
    @api.constrains('test_score', 'hr_score')
    def _check_score_limits(self):
        for record in self:
            for field_name in ['test_score', 'hr_score']:
                value = getattr(record, field_name)
                if value < 0 or value > 100:
                    raise ValidationError("Yêu cầu nhập lại điểm ")

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
  

#Nhóm 4: Cập nhất điểm
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

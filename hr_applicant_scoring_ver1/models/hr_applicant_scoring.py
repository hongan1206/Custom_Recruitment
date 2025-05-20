from odoo import models, fields, api
import logging 
_logger = logging.getLogger(__name__)

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    # Các trường điểm
    cv_score = fields.Float(
        string="CV Score",
        help="Score calculated from CV analysis (AI, Regex, OCR, etc.)"
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
        store=True,
        help="Automatically calculated average score"
    )

    matching_score = fields.Float(
        string="Matching Score(%)",
        compute="_compute_matching_score",
        store=False,
        readonly=True,
    )

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
        
    @api.depends('cv_score', 'test_score', 'hr_score', 'matching_score')
    def _compute_avg_score(self):
        """Tính điểm trung bình từ các nguồn điểm"""
        for record in self:
            scores = [record.cv_score, record.test_score, record.hr_score, record.matching_score]
            valid_scores = [score for score in scores if score > 0]  # Chỉ tính các điểm hợp lệ (> 0)
            record.avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    def update_cv_score(self, applicant_id, new_score):
        """Cập nhật điểm CV cho một ứng viên cụ thể"""
        applicant = self.browse(applicant_id)
        if applicant:
            applicant.cv_score = new_score

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
        _logger.info("hr_scoring: create called with vals_list=%s", vals_list)
        for vals in vals_list:
            job_id = vals.get('job_id')
            candidate_skill_ids = vals.get('candidate_skill_ids', [])
            if job_id:
                job = self.env['hr.job'].browse(job_id)
                # Collect existing skill_ids from vals
                existing_skill_ids = {skill[2]['skill_id'] for skill in candidate_skill_ids if skill[0] == 0 and 'skill_id' in skill[2]}
                skill_lines = []
                for skill in job.skill_ids:
                    if skill.id not in existing_skill_ids:
                        default_level = skill.skill_type_id.skill_level_ids.filtered('default_level') or skill.skill_type_id.skill_level_ids[:1]
                        skill_lines.append((0, 0, {
                            'skill_id': skill.id,
                            'skill_type_id': skill.skill_type_id.id,
                            'skill_level_id': default_level and default_level.id or False,
                        }))
                vals['candidate_skill_ids'] = candidate_skill_ids + skill_lines
                _logger.info("hr_scoring: candidate_skill_ids set to %s for job_id=%s", vals['candidate_skill_ids'], job_id)
        return super().create(vals_list)

    @api.onchange('job_id')
    def _onchange_job_id(self):
        _logger.info("hr_scoring: _onchange_job_id called for applicant id=%s, job_id=%s", self.id, self.job_id.id if self.job_id else None)
        if self.job_id:
            existing_skill_ids = {cs.skill_id.id for cs in self.candidate_skill_ids if cs.skill_id}
            skill_lines = []
            for skill in self.job_id.skill_ids:
                if skill.id not in existing_skill_ids:
                    default_level = skill.skill_type_id.skill_level_ids.filtered('default_level') or skill.skill_type_id.skill_level_ids[:1]
                    skill_lines.append((0, 0, {
                        'skill_id': skill.id,
                        'skill_type_id': skill.skill_type_id.id,
                        'skill_level_id': default_level and default_level.id or False,
                    }))
            if skill_lines:
                self.candidate_skill_ids = [(4, cs.id) for cs in self.candidate_skill_ids] + skill_lines
            _logger.info("hr_scoring: candidate_skill_ids updated for job_id=%s", self.job_id.id)
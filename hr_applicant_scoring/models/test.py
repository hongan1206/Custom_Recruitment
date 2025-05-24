from odoo import api, fields, models

class CandidateSkill(models.Model):
    _inherit = 'hr.candidate.skill'

    @api.model_create_multi
    def create(self, vals_list):
        candidate_skills = super().create(vals_list)

        for vals in vals_list:
            if 'candidate_id' in vals:
                candidate = self.env['hr.candidate'].browse(vals['candidate_id'])
                applicants = self.env['hr.applicant'].search([('candidate_id', '=', candidate.id)])
                for applicant in applicants:
                    if applicant.job_id and applicant.job_id.skill_ids:
                        for skill in applicant.job_id.skill_ids:
                            skill_type = skill.skill_type_id
                            default_level = skill_type.skill_level_ids.filtered(lambda s: s.default_level)[:1] or skill_type.skill_level_ids[:1]
                            exists = self.env['hr.candidate.skill'].search_count([
                                ('candidate_id', '=', candidate.id),
                                ('skill_id', '=', skill.id)
                            ])
                            if not exists:
                                self.env['hr.candidate.skill'].create({
                                    'candidate_id': candidate.id,
                                    'skill_id': skill.id,
                                    'skill_type_id': skill_type.id,
                                    'skill_level_id': default_level.id if default_level else False,
                                })
        return candidate_skills
    
class HrApplicant(models.Model):
    _inherit = 'hr.applicant'



    required_skill_ids = fields.Many2many(
        'hr.skill',
        'hr_applicant_required_skill_rel',
        'applicant_id',
        'skill_id',
        string='Required Skills',
        compute='_compute_required_skills',
        store=True
    )

        # Trường kỹ năng chính


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

    @api.depends('job_id')
    def _compute_required_skills(self):
        for applicant in self:
            applicant.required_skill_ids = applicant.job_id.skill_ids

    @api.depends('candidate_id.candidate_skill_ids.skill_level_id')
    def _compute_screening_score(self):
        for applicant in self:
            skills = applicant.candidate_id.candidate_skill_ids
            levels = skills.mapped('skill_level_id.level_progress')
            applicant.screening_score = sum(levels) / len(levels) if levels else 0.0


class HrApplicantSkill(models.Model):
    _name = 'hr.applicant.skill'
    _description = 'Applicant Skill'
    _order = 'skill_type_id, id'


    # Liên kết về ứng viên
    applicant_id = fields.Many2one('hr.applicant', required=True, ondelete='cascade')

    # Loại kỹ năng (IT, Language, etc)
    skill_type_id = fields.Many2one('hr.skill.type', required=True)

    # Tên kỹ năng
    skill_id = fields.Many2one(
        'hr.skill',
        required=True,
        domain="[('skill_type_id', '=', skill_type_id)]"
    )

    # Trình độ kỹ năng (Beginner, Intermediate...)
    skill_level_id = fields.Many2one(
        'hr.skill.level',
        domain="[('skill_type_id', '=', skill_type_id)]"
    )

    # Mức độ tiến triển (0 - 100%)
    level_progress = fields.Integer(default=0)
    _sql_constraints = [
        ('unique_skill', 'unique (applicant_id, skill_id)', 'An applicant can only have a skill once.')
    ]
    
    @api.constrains('skill_id', 'skill_type_id')
    def _check_skill_type(self):
        for applicant_skill in self:
            if applicant_skill.skill_id not in applicant_skill.skill_type_id.skill_ids:
                raise ValidationError(_("The skill %(name)s and skill type %(type)s doesn't match", name=applicant_skill.skill_id.name, type=applicant_skill.skill_type_id.name))

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        for applicant_skill in self:
            if applicant_skill.skill_level_id not in applicant_skill.skill_type_id.skill_level_ids:
                raise ValidationError(_("The skill level %(level)s is not valid for skill type: %(type)s", level=applicant_skill.skill_level_id.name, type=applicant_skill.skill_type_id.name))

    @api.depends('skill_type_id')
    def _compute_skill_id(self):
        for applicant_skill in self:
            if applicant_skill.skill_id.skill_type_id != applicant_skill.skill_type_id:
                applicant_skill.skill_id = False

    @api.depends('skill_id')
    def _compute_skill_level_id(self):
        for applicant_skill in self:
            if not applicant_skill.skill_id:
                applicant_skill.skill_level_id = False
            else:
                skill_levels = applicant_skill.skill_type_id.skill_level_ids
                applicant_skill.skill_level_id = skill_levels.filtered('default_level') or skill_levels[0] if skill_levels else False


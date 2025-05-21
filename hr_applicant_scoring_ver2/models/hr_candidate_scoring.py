from odoo import models, fields, api
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
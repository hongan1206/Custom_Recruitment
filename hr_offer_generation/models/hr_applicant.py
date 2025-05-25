from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    offer_ids = fields.One2many('hr.offer', 'applicant_id', string='Offers')

    def action_generate_offer(self):
        self.ensure_one()
        if not self.partner_name:
            raise UserError(_('The applicant must have a name.'))
        
        offer = self.env['hr.offer'].create({
            'applicant_id': self.id,
            'job_id': self.job_id.id,
            'company_id': self.company_id.id,
            'start_date': fields.Date.today(),
        })

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.offer',
            'res_id': offer.id,
            'views': [(False, 'form')],
            'context': {'active_model': 'hr.applicant', 'default_applicant_id': self.id}
        }

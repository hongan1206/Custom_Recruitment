from odoo import models, fields, api, _

class HrOffer(models.Model):
    _name = 'hr.offer'
    _description = 'Job Offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Offer Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    salary = fields.Monetary(string='Salary', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    start_date = fields.Date(string='Start Date')
    description = fields.Html(string='Offer Description')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Generate a name like "Offer for [Applicant Name] - [Job Position]"
            applicant = self.env['hr.applicant'].browse(vals.get('applicant_id'))
            job = self.env['hr.job'].browse(vals.get('job_id'))
            if applicant and applicant.partner_name:
                job_name = job.name if job else ''
                vals['name'] = f'Offer for {applicant.partner_name} - {job_name}'
            else:
                vals['name'] = _('New Offer')
        return super().create(vals_list)

    def action_send_by_email(self):
        self.ensure_one()
        if not self.applicant_id.email_from:
            raise UserError(_('The applicant must have an email address.'))
        
        template = self.env.ref('hr_offer_generation.email_template_offer', raise_if_not_found=False)
        if not template:
            raise UserError(_('No email template found for sending offers.'))

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': {
                'default_model': 'hr.offer',
                'default_res_ids': [self.id],
                'default_template_id': template.id,
                'force_email': True,
            },
        }

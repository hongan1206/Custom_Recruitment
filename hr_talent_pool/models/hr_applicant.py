from odoo import fields, models, api
from odoo.tools.translate import _

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    talent_pool_ids = fields.Many2many(
        comodel_name="hr.talent.pool",
        string="Talent Pools",
        groups="base.group_user"
    )
    pool_applicant_id = fields.Many2one("hr.applicant")
    is_pool_applicant = fields.Boolean(compute="_compute_is_pool")
    is_applicant_in_pool = fields.Boolean(
        compute="_compute_is_applicant_in_pool",
        search="_search_is_applicant_in_pool"
    )
    talent_pool_count = fields.Integer(compute="_compute_talent_pool_count")

    @api.depends("talent_pool_ids", "pool_applicant_id.talent_pool_ids")
    def _compute_talent_pool_count(self):
        for applicant in self:
            # Directly linked applications
            applicant.talent_pool_count = len(applicant.talent_pool_ids)
            # Indirectly linked applications
            if applicant.pool_applicant_id:
                applicant.talent_pool_count += len(applicant.pool_applicant_id.talent_pool_ids)

    @api.depends("talent_pool_ids")
    def _compute_is_pool(self):
        for applicant in self:
            applicant.is_pool_applicant = bool(applicant.talent_pool_ids)

    @api.depends(
        "talent_pool_ids", "pool_applicant_id", "email_normalized", "partner_phone_sanitized", "linkedin_profile", "active"
    )
    def _compute_is_applicant_in_pool(self):
        """
        Computes if an application is linked to a talent pool or not.
        An application can either be directly or indirectly linked to a talent pool.
        Direct link:
            - 1. Application has talent_pool_ids set, meaning this application
                is a talent pool application, or talent for short.
            - 2. Application has pool_applicant_id set, meaning this application
            is a copy or directly linked to a talent (scenario 1)

        Indirect link:
            - 3. Application shares a phone number, email, or linkedin with a
                directly linked application.

        Note: While possible, linking an application to a pool through linking
        it to an indirect link is currently excluded from the implementation
        for technical reasons.
        """
        # First, handle direct links (both active and inactive)
        direct = self.filtered(lambda a: a.talent_pool_ids or a.pool_applicant_id)
        direct.is_applicant_in_pool = True
        indirect = self - direct

        if not indirect:
            return

        # For indirect links, we need to check for matching contact info
        all_emails = {a.email_normalized for a in indirect if a.email_normalized}
        all_phones = {a.partner_phone_sanitized for a in indirect if a.partner_phone_sanitized}
        all_linkedins = {a.linkedin_profile for a in indirect if a.linkedin_profile}

        # Build domain for finding matching pool applicants
        epl_domain = []
        if all_emails:
            epl_domain.append(('email_normalized', 'in', list(all_emails)))
        if all_phones:
            epl_domain.append(('partner_phone_sanitized', 'in', list(all_phones)))
        if all_linkedins:
            epl_domain.append(('linkedin_profile', 'in', list(all_linkedins)))

        # Safe OR domain construction
        if len(epl_domain) > 2:
            domain = ['|'] * (len(epl_domain) - 1)
            for cond in epl_domain:
                domain.append(cond)
        elif len(epl_domain) == 2:
            domain = ['|'] + epl_domain
        elif len(epl_domain) == 1:
            domain = epl_domain
        else:
            domain = []

        # Find pool applicants (both active and inactive) with matching contact info
        if domain:
            # Remove active_test to include both active and inactive records
            in_pool_applicants = self.env["hr.applicant"].with_context(active_test=False).search([
                ('talent_pool_ids', '!=', False)
            ]).filtered_domain(domain)
            in_pool_data = {"emails": set(), "phones": set(), "linkedins": set()}
            for applicant in in_pool_applicants:
                if applicant.email_normalized:
                    in_pool_data["emails"].add(applicant.email_normalized)
                if applicant.partner_phone_sanitized:
                    in_pool_data["phones"].add(applicant.partner_phone_sanitized)
                if applicant.linkedin_profile:
                    in_pool_data["linkedins"].add(applicant.linkedin_profile)
            # Set is_applicant_in_pool based on matching contact info
            for applicant in indirect:
                applicant.is_applicant_in_pool = (
                    (applicant.email_normalized and applicant.email_normalized in in_pool_data["emails"]) or
                    (applicant.partner_phone_sanitized and applicant.partner_phone_sanitized in in_pool_data["phones"]) or
                    (applicant.linkedin_profile and applicant.linkedin_profile in in_pool_data["linkedins"])
                )
        else:
            # No contact info to match on
            indirect.is_applicant_in_pool = False

    def _search_is_applicant_in_pool(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s') % operator)
            
        # When searching for applicants in pool
        if (operator == '=' and value) or (operator == '!=' and not value):
            # Include both active and inactive records in the search
            self = self.with_context(active_test=False)
            # applicant is in pool if it has a pool_applicant_id or talent_pool_ids
            return ['|', ('pool_applicant_id', '!=', False), ('talent_pool_ids', '!=', False)]
        else:
            # applicant is not in pool if it has neither pool_applicant_id nor talent_pool_ids
            # For negative search, we still want to include inactive records
            self = self.with_context(active_test=False)
            return [('pool_applicant_id', '=', False), ('talent_pool_ids', '=', False)]

    def action_talent_pool_add_applicants(self):
        return {
            "name": _("Add applicant(s) to the pool"),
            "type": "ir.actions.act_window",
            "res_model": "talent.pool.add.applicants",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "is_modal": True,
                "dialog_size": "medium",
                "default_talent_pool_ids": self.env.context.get(
                    "default_talent_pool_ids"
                )
                or [],
                "default_applicant_ids": self.ids,
            },
        }
        
    def action_remove_from_talent_pool(self):
        """Remove the selected applicants from their talent pools without deleting them."""
        self.ensure_one()
        if not self.talent_pool_ids and not self.pool_applicant_id:
            return
            
        # If this is a pool applicant, update all linked applications
        if self.talent_pool_ids:
            # Find all applications linked to this pool applicant
            linked_applications = self.env['hr.applicant'].search([
                ('pool_applicant_id', '=', self.id)
            ])
            # Remove the link from all linked applications
            linked_applications.write({'pool_applicant_id': False})
            # Clear the talent pool associations
            self.write({'talent_pool_ids': [(5, 0, 0)]})
        # If this is a regular application linked to a pool applicant
        elif self.pool_applicant_id:
            self.write({'pool_applicant_id': False})
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

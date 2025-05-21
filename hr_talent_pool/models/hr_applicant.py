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
        "talent_pool_ids", "pool_applicant_id", "email_normalized", "partner_phone_sanitized", "linkedin_profile"
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
                direclty linked application.

        Note: While possible, linking an application to a pool through linking
        it to an indirect link is currently excluded from the implementation
        for technical reasons.
        """
        direct = self.filtered(lambda a: a.talent_pool_ids or a.pool_applicant_id)
        direct.is_applicant_in_pool = True
        indirect = self - direct

        if not indirect:
            return

        all_emails = {a.email_normalized for a in indirect if a.email_normalized}
        all_phones = {a.partner_phone_sanitized for a in indirect if a.partner_phone_sanitized}
        all_linkedins = {a.linkedin_profile for a in indirect if a.linkedin_profile}

        epl_domain = []
        if all_emails:
            epl_domain = [('email_normalized', 'in', list(all_emails))]
        elif all_phones:
            epl_domain = [('partner_phone_sanitized', 'in', list(all_phones))]
        elif all_linkedins:
            epl_domain = [('linkedin_profile', 'in', list(all_linkedins))]

        pool_domain = [('talent_pool_ids', '!=', False), ('pool_applicant_id', '!=', False)]
        domain = ['&'] + pool_domain + epl_domain
        in_pool_applicants = self.env["hr.applicant"].with_context(active_test=True).search(domain)
        in_pool_data = {"emails": set(), "phones": set(), "linkedins": set()}

        for applicant in in_pool_applicants:
            if applicant.email_normalized:
                in_pool_data["emails"].add(applicant.email_normalized)
            if applicant.partner_phone_sanitized:
                in_pool_data["phones"].add(applicant.partner_phone_sanitized)
            if applicant.linkedin_profile:
                in_pool_data["linkedins"].add(applicant.linkedin_profile)

        for applicant in indirect:
            applicant.is_applicant_in_pool = (
                applicant.email_normalized in in_pool_data["emails"]
                or applicant.partner_phone_sanitized in in_pool_data["phones"]
                or applicant.linkedin_profile in in_pool_data["linkedins"]
            )

    def _search_is_applicant_in_pool(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s') % operator)
        if (operator == '=' and value) or (operator == '!=' and not value):
            # applicant is in pool if it has a pool_applicant_id or talent_pool_ids
            return ['|', ('pool_applicant_id', '!=', False), ('talent_pool_ids', '!=', False)]
        else:
            # applicant is not in pool if it has neither pool_applicant_id nor talent_pool_ids
            return [('pool_applicant_id', '=', False), ('talent_pool_ids', '=', False)]

    def _search_is_applicant_in_pool(self, operator, value):
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s') % operator)
        if (operator == '=' and value) or (operator == '!=' and not value):
            # applicant is in pool if it has a pool_applicant_id or talent_pool_ids
            return ['|', ('pool_applicant_id', '!=', False), ('talent_pool_ids', '!=', False)]
        else:
            # applicant is not in pool if it has neither pool_applicant_id nor talent_pool_ids
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

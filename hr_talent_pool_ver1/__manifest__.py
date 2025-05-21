# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Talent Pool',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'sequence': 91,
    'summary': 'Manage your talent pool of potential candidates',
    'depends': [
        'hr',
        'base',
        'hr_recruitment',
    ],
    'data': [
        'security/hr_talent_pool_security.xml',
        'security/ir.model.access.csv',
        'views/hr_applicant_views.xml',
        'views/hr_talent_pool_views.xml',
        'views/hr_talent_pool_actions.xml',
        'views/menuitems.xml',
        'wizard/talent_pool_add_applicants_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

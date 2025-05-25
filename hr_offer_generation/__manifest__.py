{'name': 'HR Offer Generation',
 'version': '18.0.1.0.0',
 'category': 'Human Resources',
 'summary': 'Generate offers for HR applicants',
 'description': """
This module adds functionality to generate job offers for HR applicants.
""",
 'depends': ['hr_recruitment'],
 'data': [
     'security/ir.model.access.csv',
     'views/hr_applicant_views.xml',
     'views/hr_offer_views.xml',
     'data/email_template_offer.xml',
 ],
 'installable': True,
 'application': False,
 'auto_install': False,
 'license': 'LGPL-3',
}

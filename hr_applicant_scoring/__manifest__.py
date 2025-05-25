{'name': 'HR Applicant Scoring',
 'version': '1.0',
 'category': 'Human Resources',
 'summary': 'Scoring system for HR applicants',
 'description': """
 This module adds scoring functionality to HR applicants.
 """,
 'depends': ['base', 'hr_recruitment', 'hr_recruitment_skills', 'hr_skills','hr_recruitment_survey'],
 'data': [
     'views/hr_applicant_scoring.xml',
 ],
 'installable': True,
 'application': False,
 'auto_install': False,
 'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-

{
    'name': "Zalo Configuration",
    'summary': "Zalo Configuration",
    'description': "Zalo Configuration",
    # for the full list
    'version': '16.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
    ],
    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/zalo_configuration_views.xml',
    ],
}

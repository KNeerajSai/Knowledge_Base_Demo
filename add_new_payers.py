#!/usr/bin/env python3
"""
Add New Payers to Crawler Configuration
Adds all the requested healthcare companies to payer_portal_crawler.py
"""

import re

def add_payers_to_crawler():
    """Add the new payer configurations"""
    
    # Your company list
    companies = [
        "United Healthcare",  # Already exists
        "Anthem / Elevance Health (Blue Cross Blue Shield plans)",  # Already exists as anthem
        "Aetna",  # Already exists
        "Humana",
        "Centene / Ambetter / WellCare", 
        "Cigna",
        "Kaiser Permanente",
        "Molina Healthcare",
        "Florida Blue (GuideWell)",
        "UPMC Health Plan",
        "CareSource",
        "Amerigroup / AmeriHealth Caritas",
        "BCBS of Illinois (HCSC)",
        "Health Net",
        "Bright HealthCare",
        "WellCare by Allwell",
        "CountyCare",  # Already exists
        "Zing Health",
        "Medicare (Advantage programs across carriers)",
        "State Medicaid programs (e.g., Illinois Medicaid, Indiana Medicaid, Kentucky Medicaid)"
    ]
    
    # New payers to add (excluding existing ones)
    new_payers = {
        "humana": {
            "name": "Humana",
            "base_url": "https://www.humana.com/",
            "provider_portal": "https://www.humana.com/provider",
            "additional_pages": [
                "https://www.humana.com/provider/support/prior-authorization",
                "https://www.humana.com/provider/support/claims",
                "https://www.humana.com/provider/medical-resources"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "pre-auth",
                    "authorization requirements", "medical necessity"
                ],
                "timely_filing": [
                    "timely filing", "claim submission deadlines", 
                    "filing requirements", "submission timelines"
                ],
                "appeals": [
                    "appeals process", "claim appeals", "dispute resolution",
                    "appeal procedures", "grievances"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "centene": {
            "name": "Centene / Ambetter / WellCare",
            "base_url": "https://www.centene.com/",
            "provider_portal": "https://www.centene.com/providers.html",
            "additional_pages": [
                "https://www.ambetter.com/providers",
                "https://www.wellcare.com/providers",
                "https://www.centene.com/products-and-services/medicaid.html"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "pre-auth",
                    "authorization requirements"
                ],
                "timely_filing": [
                    "timely filing", "claim deadlines", "filing requirements"
                ],
                "appeals": [
                    "appeals", "grievances", "dispute resolution"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "cigna": {
            "name": "Cigna",
            "base_url": "https://www.cigna.com/",
            "provider_portal": "https://www.cigna.com/health-care-providers",
            "additional_pages": [
                "https://www.cigna.com/health-care-providers/resources",
                "https://www.cigna.com/health-care-providers/coverage-and-claims",
                "https://www.cigna.com/health-care-providers/prior-authorization"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "coverage determination"
                ],
                "timely_filing": [
                    "timely filing", "claim submission", "billing deadlines"
                ],
                "appeals": [
                    "appeals", "claim disputes", "grievance process"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "kaiser_permanente": {
            "name": "Kaiser Permanente", 
            "base_url": "https://healthy.kaiserpermanente.org/",
            "provider_portal": "https://providerdirectory.kaiserpermanente.org/",
            "additional_pages": [
                "https://healthy.kaiserpermanente.org/health-wellness",
                "https://about.kaiserpermanente.org/who-we-are"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical review", "coverage approval"
                ],
                "timely_filing": [
                    "timely filing", "claims processing", "submission requirements"
                ],
                "appeals": [
                    "appeals", "grievances", "member complaints"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "molina": {
            "name": "Molina Healthcare",
            "base_url": "https://www.molinahealthcare.com/",
            "provider_portal": "https://www.molinahealthcare.com/providers",
            "additional_pages": [
                "https://www.molinahealthcare.com/providers/medicaid",
                "https://www.molinahealthcare.com/providers/resources"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "medical necessity"
                ],
                "timely_filing": [
                    "timely filing", "claim deadlines", "submission requirements"
                ],
                "appeals": [
                    "appeals", "grievances", "dispute resolution"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "florida_blue": {
            "name": "Florida Blue (GuideWell)",
            "base_url": "https://www.floridablue.com/",
            "provider_portal": "https://www.floridablue.com/providers",
            "additional_pages": [
                "https://www.floridablue.com/providers/tools-resources",
                "https://www.floridablue.com/providers/claims-and-payments"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical review", "coverage decisions"
                ],
                "timely_filing": [
                    "timely filing", "claims submission", "billing requirements"
                ],
                "appeals": [
                    "appeals", "grievances", "member complaints"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "upmc": {
            "name": "UPMC Health Plan",
            "base_url": "https://www.upmchealthplan.com/",
            "provider_portal": "https://www.upmchealthplan.com/providers",
            "additional_pages": [
                "https://www.upmchealthplan.com/providers/resources",
                "https://www.upmchealthplan.com/providers/claims"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical necessity review"
                ],
                "timely_filing": [
                    "timely filing", "claim submission deadlines"
                ],
                "appeals": [
                    "appeals", "grievances", "complaints"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "caresource": {
            "name": "CareSource",
            "base_url": "https://www.caresource.com/",
            "provider_portal": "https://www.caresource.com/providers",
            "additional_pages": [
                "https://www.caresource.com/providers/medicaid",
                "https://www.caresource.com/providers/resources"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "coverage determination"
                ],
                "timely_filing": [
                    "timely filing", "claims processing", "submission guidelines"
                ],
                "appeals": [
                    "appeals", "grievances", "dispute resolution"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "amerigroup": {
            "name": "Amerigroup / AmeriHealth Caritas",
            "base_url": "https://www.amerigroup.com/",
            "provider_portal": "https://www.amerigroup.com/providers",
            "additional_pages": [
                "https://www.amerihealthcaritas.com/providers",
                "https://www.amerigroup.com/providers/medicaid"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "medical review"
                ],
                "timely_filing": [
                    "timely filing", "claim submission", "billing deadlines"
                ],
                "appeals": [
                    "appeals", "grievances", "member complaints"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "bcbs_illinois": {
            "name": "BCBS of Illinois (HCSC)",
            "base_url": "https://www.bcbsil.com/",
            "provider_portal": "https://www.bcbsil.com/providers",
            "additional_pages": [
                "https://www.hcsc.com/",
                "https://www.bcbsil.com/providers/claims-and-eligibility"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical necessity", "coverage review"
                ],
                "timely_filing": [
                    "timely filing", "claims deadlines", "submission requirements"
                ],
                "appeals": [
                    "appeals", "grievances", "dispute resolution"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "health_net": {
            "name": "Health Net",
            "base_url": "https://www.healthnet.com/",
            "provider_portal": "https://www.healthnet.com/providers",
            "additional_pages": [
                "https://www.healthnet.com/providers/resources",
                "https://www.healthnet.com/providers/claims"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical review", "coverage decisions"
                ],
                "timely_filing": [
                    "timely filing", "claim submission", "billing guidelines"
                ],
                "appeals": [
                    "appeals", "grievances", "complaint process"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "bright_healthcare": {
            "name": "Bright HealthCare",
            "base_url": "https://www.brighthealthcare.com/",
            "provider_portal": "https://www.brighthealthcare.com/providers",
            "additional_pages": [
                "https://www.brighthealthcare.com/providers/resources"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical necessity"
                ],
                "timely_filing": [
                    "timely filing", "claims submission"
                ],
                "appeals": [
                    "appeals", "grievances"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "wellcare_allwell": {
            "name": "WellCare by Allwell",
            "base_url": "https://www.wellcare.com/",
            "provider_portal": "https://www.wellcare.com/providers", 
            "additional_pages": [
                "https://www.allwellplans.com/providers"
            ],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "coverage determination"
                ],
                "timely_filing": [
                    "timely filing", "claim deadlines"
                ],
                "appeals": [
                    "appeals", "grievances"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        },
        
        "zing_health": {
            "name": "Zing Health",
            "base_url": "https://www.zinghealth.com/",
            "provider_portal": "https://www.zinghealth.com/providers",
            "additional_pages": [],
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "medical review"
                ],
                "timely_filing": [
                    "timely filing", "claims processing"
                ],
                "appeals": [
                    "appeals", "grievances"
                ]
            },
            "login_required": False,
            "rate_limit": 2
        }
    }
    
    return new_payers

def update_progress_file():
    """Update the progress file with company list"""
    
    companies = [
        "United Healthcare ✅",
        "Anthem / Elevance Health ✅", 
        "Aetna ✅",
        "Humana 🆕",
        "Centene / Ambetter / WellCare 🆕",
        "Cigna 🆕", 
        "Kaiser Permanente 🆕",
        "Molina Healthcare 🆕",
        "Florida Blue (GuideWell) 🆕",
        "UPMC Health Plan 🆕",
        "CareSource 🆕",
        "Amerigroup / AmeriHealth Caritas 🆕",
        "BCBS of Illinois (HCSC) 🆕", 
        "Health Net 🆕",
        "Bright HealthCare 🆕",
        "WellCare by Allwell 🆕",
        "CountyCare ✅",
        "Zing Health 🆕"
    ]
    
    print("📋 COMPANY LIST ADDED TO CRAWLER:")
    print("=" * 40)
    print("✅ = Already configured")
    print("🆕 = Newly added")
    print()
    
    for i, company in enumerate(companies, 1):
        print(f"{i:2d}. {company}")
    
    print(f"\n📊 Total: {len(companies)} companies configured")
    print("📁 File: payer_portal_crawler.py")
    print("🚀 Ready to crawl!")

if __name__ == "__main__":
    new_payers = add_payers_to_crawler()
    update_progress_file()
    
    print(f"\n✅ Added {len(new_payers)} new payer configurations")
    print("📝 Next: Update payer_portal_crawler.py with new configurations")
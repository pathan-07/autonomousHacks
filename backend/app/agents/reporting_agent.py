class ReportingAgent:
    def generate_draft(self, input_data: str, analysis_result: dict) -> dict | None:
        """
        Creates a formal complaint draft for the Indian Cyber Crime Portal.
        """
        score = analysis_result.get("risk_score", 0)

        # Only suggest reporting for High/Severe risks
        if score < 75:
            return None

        category = analysis_result.get("category", "Online Fraud")
        reasoning = analysis_result.get("reasoning", "Suspicious activity detected by AI.")

        # Formal Complaint Template
        draft_text = f"""
[SUBJECT]: Reporting Suspected {category} - Urgent

To the Cyber Crime Cell,

I wish to report a suspected fraudulent attempt received via digital communication.
Below are the details for your investigation:

1. SUSPECTED CONTENT:
\"{input_data}\"

2. AI FORENSIC ANALYSIS:
An automated security system flagged this content with a Risk Score of {score}/100.
Key indicators identified: {reasoning}

3. REQUEST:
Please verify the source and take necessary action to prevent financial loss to other citizens.

Sincerely,
[Concerned Citizen]
        """

        return {
            "is_reportable": True,
            "portal_url": "https://cybercrime.gov.in",
            "email_subject": f"Complaint: {category} Attempt",
            "email_body": draft_text.strip(),
        }

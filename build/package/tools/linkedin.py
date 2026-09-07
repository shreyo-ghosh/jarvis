"""
tools/linkedin.py — LinkedIn post prompt template.
"""


def generate_linkedin_post(topic: str) -> str:
    return (
        f"Draft a LinkedIn post about: {topic}\n"
        f"Style: first-person, practical, no corporate buzzwords, "
        f"3-4 short paragraphs, end with a soft call-to-action. "
        f"Audience: Indian small business owners and retail investors."
    )

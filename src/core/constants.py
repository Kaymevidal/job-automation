from enum import Enum


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    IN_REVIEW = "in_review"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class ExperienceLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class ScraperSource(str, Enum):
    REMOTEOK = "remoteok"
    VAGAS_COM_BR = "vagas_com_br"
    INFOJOBS = "infojobs"
    CATHO = "catho"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    MANUAL = "manual"


MIN_COMPATIBILITY_SCORE = 0.6

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ============================================================
# Common College Validation
# ============================================================

ALLOWED_AFFILIATION_STATUS = {
    "affiliated",
    "self_university",
}

ALLOWED_INSTITUTION_TYPES = {
    "Government",
    "Private",
    "Government Aided",
    "Autonomous",
    "Deemed University",
    "University Department",
}


# ============================================================
# College Profile Create
# ============================================================

class CollegeProfileCreate(BaseModel):

    # --------------------------------------------------------
    # Institution Identity
    # --------------------------------------------------------

    name: str

    # Public College ID entered by the college itself.
    # Example: MGM095
    college_public_id: str

    # Official college logo / profile image URL.
    # The image itself should be stored in persistent object storage.
    college_logo_url: str | None = None

    affiliation_status: Literal[
        "affiliated",
        "self_university",
    ]

    university: str | None = None

    college_code: str
    aishe_code: str

    institution_type: str | None = None

    established_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    # --------------------------------------------------------
    # Official Contact
    # --------------------------------------------------------

    website: str
    official_email: str
    official_phone: str

    address: str
    city: str
    state: str

    pincode: str | None = None

    # --------------------------------------------------------
    # Authorized Person
    # --------------------------------------------------------

    principal_name: str

    authorized_person_name: str
    authorized_designation: str

    authorized_email: str
    authorized_phone: str

    # --------------------------------------------------------
    # Security
    # --------------------------------------------------------

    model_config = ConfigDict(
        extra="forbid"
    )

    # --------------------------------------------------------
    # Basic String Cleanup
    # --------------------------------------------------------

    @field_validator(
        "name",
        "college_public_id",
        "college_code",
        "aishe_code",
        "website",
        "official_email",
        "official_phone",
        "address",
        "city",
        "state",
        "principal_name",
        "authorized_person_name",
        "authorized_designation",
        "authorized_email",
        "authorized_phone",
    )
    @classmethod
    def validate_required_string(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "This field cannot be empty"
            )

        return value

    # --------------------------------------------------------
    # Normalize Codes
    # --------------------------------------------------------

    @field_validator(
        "college_public_id",
        "college_code",
        "aishe_code",
    )
    @classmethod
    def normalize_codes(
        cls,
        value: str,
    ) -> str:

        return value.strip().upper()

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    @field_validator(
        "official_email",
        "authorized_email",
    )
    @classmethod
    def normalize_email(
        cls,
        value: str,
    ) -> str:

        value = value.strip().lower()

        if (
            "@" not in value
            or "." not in value.split("@")[-1]
        ):
            raise ValueError(
                "Invalid email address"
            )

        return value

    # --------------------------------------------------------
    # College Logo URL
    # --------------------------------------------------------

    @field_validator("college_logo_url")
    @classmethod
    def validate_college_logo_url(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "College logo URL must start with http:// or https://"
            )

        return value

    # --------------------------------------------------------
    # Website
    # --------------------------------------------------------

    @field_validator("website")
    @classmethod
    def validate_website(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "Website must start with http:// or https://"
            )

        return value

    # --------------------------------------------------------
    # PIN Code
    # --------------------------------------------------------

    @field_validator("pincode")
    @classmethod
    def validate_pincode(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if not value.isdigit():
            raise ValueError(
                "PIN code must contain only numbers"
            )

        if len(value) != 6:
            raise ValueError(
                "PIN code must be 6 digits"
            )

        return value

    # --------------------------------------------------------
    # Institution Type
    # --------------------------------------------------------

    @field_validator("institution_type")
    @classmethod
    def validate_institution_type(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if value not in ALLOWED_INSTITUTION_TYPES:
            raise ValueError(
                "Invalid institution type"
            )

        return value

    # --------------------------------------------------------
    # Affiliation Logic
    # --------------------------------------------------------

    @model_validator(mode="after")
    def validate_affiliation(self):

        # College affiliated to another university
        if self.affiliation_status == "affiliated":

            if (
                self.university is None
                or not self.university.strip()
            ):
                raise ValueError(
                    "Affiliated university is required"
                )

            self.university = (
                self.university.strip()
            )

        # Institution itself is a university
        elif (
            self.affiliation_status
            == "self_university"
        ):

            self.university = None

        return self


# ============================================================
# College Profile Update
# ============================================================

class CollegeProfileUpdate(BaseModel):

    name: str | None = None
    college_public_id: str | None = None
    college_logo_url: str | None = None

    affiliation_status: Literal[
        "affiliated",
        "self_university",
    ] | None = None

    university: str | None = None

    college_code: str | None = None
    aishe_code: str | None = None

    institution_type: str | None = None

    established_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    website: str | None = None

    official_email: str | None = None
    official_phone: str | None = None

    address: str | None = None

    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    principal_name: str | None = None

    authorized_person_name: str | None = None
    authorized_designation: str | None = None

    authorized_email: str | None = None
    authorized_phone: str | None = None

    model_config = ConfigDict(
        extra="forbid"
    )

    # --------------------------------------------------------
    # Normalize Codes
    # --------------------------------------------------------

    @field_validator(
        "college_public_id",
        "college_code",
        "aishe_code",
    )
    @classmethod
    def normalize_optional_codes(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "College Public ID / College code / AISHE code cannot be empty"
            )

        return value.upper()

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    @field_validator(
        "official_email",
        "authorized_email",
    )
    @classmethod
    def validate_optional_email(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip().lower()

        if not value:
            raise ValueError(
                "Email cannot be empty"
            )

        if (
            "@" not in value
            or "." not in value.split("@")[-1]
        ):
            raise ValueError(
                "Invalid email address"
            )

        return value

    # --------------------------------------------------------
    # College Logo URL
    # --------------------------------------------------------

    @field_validator("college_logo_url")
    @classmethod
    def validate_optional_college_logo_url(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "College logo URL must start with http:// or https://"
            )

        return value

    # --------------------------------------------------------
    # Website
    # --------------------------------------------------------

    @field_validator("website")
    @classmethod
    def validate_optional_website(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "Website must start with http:// or https://"
            )

        return value

    # --------------------------------------------------------
    # PIN
    # --------------------------------------------------------

    @field_validator("pincode")
    @classmethod
    def validate_optional_pincode(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if (
            not value.isdigit()
            or len(value) != 6
        ):
            raise ValueError(
                "PIN code must be 6 digits"
            )

        return value

    # --------------------------------------------------------
    # Institution Type
    # --------------------------------------------------------

    @field_validator("institution_type")
    @classmethod
    def validate_optional_institution_type(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if value not in ALLOWED_INSTITUTION_TYPES:
            raise ValueError(
                "Invalid institution type"
            )

        return value


# ============================================================
# College Profile Response
# ============================================================

class CollegeProfileResponse(BaseModel):

    id: int
    user_id: int

    name: str
    college_public_id: str | None = None
    college_logo_url: str | None = None

    affiliation_status: str | None = None
    university: str | None = None

    college_code: str | None = None
    aishe_code: str | None = None

    institution_type: str | None = None
    established_year: int | None = None

    website: str | None = None

    official_email: str | None = None
    official_phone: str | None = None

    address: str | None = None

    city: str | None = None
    state: str | None = None
    pincode: str | None = None

    principal_name: str | None = None

    authorized_person_name: str | None = None
    authorized_designation: str | None = None

    authorized_email: str | None = None
    authorized_phone: str | None = None

    # Documents
    affiliation_certificate_url: str | None = None
    authorization_letter_url: str | None = None

    # Verification — READ ONLY from client perspective
    email_verified: bool = False
    phone_verified: bool = False
    website_verified: bool = False
    documents_verified: bool = False

    verification_status: str = "pending"
    verification_note: str | None = None

    # Legacy compatibility
    is_verified: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# Department Create
# ============================================================

class DepartmentCreate(BaseModel):
    name: str
    code: str | None = None

    program_type: str | None = None

    hod_name: str | None = None
    coordinator_name: str | None = None

    official_email: str | None = None
    contact_number: str | None = None

    intake_capacity: int | None = Field(
        default=None,
        ge=1,
    )

    established_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    model_config = ConfigDict(
        extra="forbid"
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Department name is required"
            )

        return value

    @field_validator("code")
    @classmethod
    def normalize_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        return value or None

    @field_validator(
        "program_type",
        "hod_name",
        "coordinator_name",
        "contact_number",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("official_email")
    @classmethod
    def normalize_official_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()

        if not value:
            return None

        if (
            "@" not in value
            or "." not in value.split("@")[-1]
        ):
            raise ValueError(
                "Invalid department official email"
            )

        return value


# ============================================================
# Department Update
# ============================================================

class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None

    program_type: str | None = None

    hod_name: str | None = None
    coordinator_name: str | None = None

    official_email: str | None = None
    contact_number: str | None = None

    intake_capacity: int | None = Field(
        default=None,
        ge=1,
    )

    established_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        extra="forbid"
    )

    @field_validator("name")
    @classmethod
    def validate_optional_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "Department name cannot be empty"
            )

        return value

    @field_validator("code")
    @classmethod
    def normalize_optional_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        return value or None

    @field_validator(
        "program_type",
        "hod_name",
        "coordinator_name",
        "contact_number",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("official_email")
    @classmethod
    def normalize_optional_official_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()

        if not value:
            return None

        if (
            "@" not in value
            or "." not in value.split("@")[-1]
        ):
            raise ValueError(
                "Invalid department official email"
            )

        return value


# ============================================================
# Department Response
# ============================================================

class DepartmentResponse(BaseModel):
    id: int
    college_id: int

    name: str
    code: str | None = None

    program_type: str | None = None

    hod_name: str | None = None
    coordinator_name: str | None = None

    official_email: str | None = None
    contact_number: str | None = None

    intake_capacity: int | None = None
    established_year: int | None = None

    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# College Student Registry Create
# ============================================================

class CollegeStudentRegistryCreate(BaseModel):

    model_config = ConfigDict(
        extra="forbid"
    )

    student_id_number: str
    student_name: str

    department_id: int

    year: int = Field(
        ge=1,
        le=10,
    )

    # Admission / graduating batch.
    # Example: 2026-2030
    batch: str | None = None

    # College section / class group.
    # Example: F2, A, CSE-A
    section: str | None = None

    @field_validator("student_id_number")
    @classmethod
    def normalize_student_id(
        cls,
        value: str,
    ) -> str:

        value = value.strip().upper()

        if not value:
            raise ValueError(
                "Student ID / Enrollment Number is required"
            )

        return value

    @field_validator("student_name")
    @classmethod
    def validate_student_name(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Student name is required"
            )

        return value


    @field_validator("batch", "section")
    @classmethod
    def normalize_optional_registry_text(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


# ============================================================
# College Student Registry Update
# ============================================================

class CollegeStudentRegistryUpdate(BaseModel):

    model_config = ConfigDict(
        extra="forbid"
    )

    student_name: str | None = None

    department_id: int | None = None

    year: int | None = Field(
        default=None,
        ge=1,
        le=10,
    )

    batch: str | None = None
    section: str | None = None

    is_active: bool | None = None

    @field_validator("student_name")
    @classmethod
    def validate_optional_student_name(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "Student name cannot be empty"
            )

        return value


    @field_validator("batch", "section")
    @classmethod
    def normalize_optional_registry_text(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


# ============================================================
# College Student Registry Response
# ============================================================

class CollegeStudentRegistryResponse(BaseModel):

    id: int
    college_id: int

    department_id: int | None = None

    student_id_number: str

    student_name: str | None = None

    year: int | None = None

    batch: str | None = None
    section: str | None = None

    is_active: bool

    claimed_student_id: int | None = None

    model_config = ConfigDict(
        from_attributes=True
    )
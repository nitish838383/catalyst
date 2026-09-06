import json

from app.core.config import settings


def generate_recruiter_response(
    recruiter_context,
    user_message,
    conversation_history=None,
):

    # =====================================================
    # FALLBACK MODE
    # OpenAI key nahi ho to basic smart response
    # =====================================================

    if not settings.OPENAI_API_KEY:

        selected_opportunity = (
            recruiter_context.get(
                "selected_opportunity"
            )
            or {}
        )

        candidates = (
            recruiter_context.get(
                "candidates"
            )
            or []
        )


        # -------------------------------------------------
        # Selected opportunity + applicants
        # -------------------------------------------------

        if selected_opportunity and candidates:

            top_candidates = (
                candidates[:5]
            )


            lines = []


            for index, candidate in enumerate(
                top_candidates,
                start=1
            ):

                lines.append(

                    f"{index}. "
                    f"{candidate['name']} "
                    f"— {candidate['match_score']}% match "
                    f"— Status: {candidate['status']}"

                )


            return (

                f"Top candidates for "
                f"{selected_opportunity['title']}:\n\n"

                + "\n".join(lines)

            )


        # -------------------------------------------------
        # Company opportunities summary
        # -------------------------------------------------

        opportunities = (
            recruiter_context.get(
                "opportunities"
            )
            or []
        )


        if opportunities:

            active_opportunities = [

                opportunity

                for opportunity
                in opportunities

                if opportunity.get(
                    "is_active"
                )

            ]


            total_applications = sum(

                opportunity.get(
                    "application_count",
                    0
                )

                for opportunity
                in opportunities

            )


            return (

                f"You currently have "
                f"{len(active_opportunities)} active opportunities "
                f"and {total_applications} total applications. "

                f"Ask about a specific opportunity ID "
                f"to review ranked candidates."

            )


        return (

            "Create at least one opportunity so I can help "
            "with applicant ranking and hiring insights."

        )


    # =====================================================
    # OPENAI MODE
    # =====================================================

    from openai import OpenAI


    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )


    context = json.dumps(
        recruiter_context,
        default=str
    )


    history = "\n".join(

        f"{message['role']}: "
        f"{message['content']}"

        for message
        in (
            conversation_history
            or []
        )[-10:]

    )


    response = client.responses.create(

        model=
            settings.OPENAI_MODEL,


        instructions=(

            "You are SkillBridge AI Hiring Intelligence Assistant. "

            "Use only the supplied recruiter/company context. "

            "Never invent applicants, students, skills, "
            "match scores, opportunities, application statuses "
            "or collaborations. "

            "Only discuss candidates who actually applied "
            "to this company's opportunities. "

            "Do not infer sensitive or protected personal traits. "

            "Rank candidates only using supplied job-relevant data "
            "such as skills, match scores, application status "
            "and opportunity requirements. "

            "Explain matched skills and missing skills clearly. "

            "Give concise and actionable hiring guidance."

        ),


        input=(

            f"RECRUITER CONTEXT:\n"
            f"{context}\n\n"

            f"RECENT HISTORY:\n"
            f"{history}\n\n"

            f"QUESTION:\n"
            f"{user_message}"

        )

    )


    return (
        response.output_text
    )
import json
from app.core.config import settings

def generate_career_response(student_context, user_message, conversation_history=None):
    if not settings.OPENAI_API_KEY:
        r=student_context.get("readiness") or {}; match=(student_context.get("selected_opportunity") or {}).get("match")
        if match:
            return f"Your current match is {match['score']}%. Matched skills: {', '.join(match['matched_skills']) or 'none'}. Missing from your profile: {', '.join(match['missing_skills']) or 'none'}."
        if r:
            return f"Your current readiness for {r['target_role']} is {r['readiness_score']}%. Strong/matched skills: {', '.join(r['matched_skills']) or 'none'}. Priority gaps: {', '.join(r['missing_skills']) or 'none'}."
        return "Add your career goal and skills so I can give personalized guidance."
    from openai import OpenAI
    client=OpenAI(api_key=settings.OPENAI_API_KEY)
    context=json.dumps(student_context,default=str)
    history="\n".join(f"{m['role']}: {m['content']}" for m in (conversation_history or [])[-10:])
    resp=client.responses.create(model=settings.OPENAI_MODEL,instructions="You are SkillBridge AI Career Assistant. Use only supplied student context, do not invent skills, explain gaps and give concise actionable guidance.",input=f"STUDENT CONTEXT:\n{context}\nRECENT HISTORY:\n{history}\nQUESTION:\n{user_message}")
    return resp.output_text

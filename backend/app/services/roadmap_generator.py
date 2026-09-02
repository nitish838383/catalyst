ROADMAP_CONTENT={
"fastapi":"Learn routing, validation, dependencies and build a REST API.","postgresql":"Learn relational modeling, joins and indexes.",
"rest api":"Learn REST conventions, HTTP methods and status codes.","docker":"Containerize and run your backend consistently.",
"git":"Practice branching, commits and pull requests.","react":"Build reusable components and API-driven UI.",
"javascript":"Strengthen ES6+, async/await and DOM fundamentals."
}
def generate_roadmap_steps(missing_skills):
    steps=[]
    for i,s in enumerate(missing_skills,1):
        steps.append({"step_number":i,"title":f"Learn {s.title()}","skill_name":s,"description":ROADMAP_CONTENT.get(s,f"Learn and practice {s} with a small project.")})
    steps.append({"step_number":len(steps)+1,"title":"Build Final Project","skill_name":None,"description":"Combine the learned skills in a deployable portfolio project."})
    return steps

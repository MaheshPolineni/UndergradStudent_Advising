import openpyxl
import re

# Grade ranking
grade_order = {"A": 4, "TA": 4, "B": 3, "TB": 3, "C": 2, "TC": 2, "D": 1, "TD": 1, "F": 0, "S": 4, "TS": 4}

def student_grades(completed_courses):
    actual_grades={}
    for course in completed_courses:
        actual_grades[course["subject"]+" "+course["number"]]=course["grade"]
    return actual_grades

def check_condition(course, operator, required_grade, student_grades):
    if course not in student_grades:
        return False
    student_grade = student_grades[course]
    if operator == ">=":
        return grade_order[student_grade] >= grade_order[required_grade]
    elif operator == ">":
        return grade_order[student_grade] > grade_order[required_grade]
    return False

def transform_expression(expr):
    def replacer(match):
        course = match.group(1).strip()
        operator = match.group(2)
        grade = match.group(3)
        return f'check_condition("{course}", "{operator}", "{grade}", student_grades)'

    # Capture full course codes like COSC 1337, MATH 2412, CPSC 2347
    # pattern = r'([A-Za-z]+\s*\d+)\s*(>=|>)\s*([A-F])'
    pattern = r'([A-Za-z]+\s*\d+)\s*(>=|>)\s*(T?[A-FS])'


    transformed = re.sub(pattern, replacer, expr)
    return transformed

def is_eligible_for_course(course, prereqs, student_grades):
    if course not in prereqs or prereqs[course].strip() == "":
        return True
    expr = prereqs[course]
    transformed_expr = transform_expression(expr)
    try:
        return eval(
            transformed_expr,
            {"__builtins__": None},
            {"check_condition": check_condition, "student_grades": student_grades}
        )
    except Exception as e:
        print(f"❌ Error evaluating prereqs for {course}: {expr}")
        print(f"   Transformed expression: {transformed_expr}")
        print(f"   Exception: {e}")
        return False
    

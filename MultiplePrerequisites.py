import openpyxl
import re

# Grade ranking
grade_order = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}

def read_student_grades_excel(filename, sheet_name="student_grades"):
    student_grades = {}
    wb = openpyxl.load_workbook(filename, data_only=True)
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
        course, grade = row
        if course and grade:
            student_grades[course.strip()] = grade.strip()
    wb.close()
    return student_grades

def read_prereqs_excel(filename, sheet_name="prereqs"):
    prereqs = {}
    wb = openpyxl.load_workbook(filename, data_only=True)
    ws = wb[sheet_name]
    for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
        course, expr = row
        if course:
            prereqs[course.strip()] = expr.strip() if expr else ""
    wb.close()
    return prereqs

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
        course = match.group(1)
        operator = match.group(2)
        grade = match.group(3)
        return f'check_condition("{course}", "{operator}", "{grade}", student_grades)'
    
    pattern = r'([A-Za-z0-9_]+)\s*(>=|>)\s*([A-F])'
    return re.sub(pattern, replacer, expr)

def is_eligible_for_course(course, prereqs, student_grades):
    if course not in prereqs or prereqs[course].strip() == "":
        return True
    expr = prereqs[course]
    transformed_expr = transform_expression(expr)
    try:
        return eval(transformed_expr, {"check_condition": check_condition, "student_grades": student_grades})
    except Exception as e:
        print(f"❌ Error evaluating prereqs for {course}: {expr}")
        print(f"   Transformed expression: {transformed_expr}")
        print(f"   Exception: {e}")
        return False


# ================================
# Example usage
# ================================

# In Excel file (e.g., prereq_data.xlsx):
# Sheet 'prereqs':
# course | prereq
# C1     | C2>=C and C3>=B
# C4     | C3>=C or C5>=B
# C6     | (C1>=B and (C5>=C or C8>C)) or (C2>=B and (C3>=C or (C9>=A and C10>=B)))

# Sheet 'student_grades':
# course | grade
# C1     | B
# C2     | B
# C3     | C
# C5     | A
# C8     | B
# C9     | A
# C10    | B

prereqs = read_prereqs_excel('prereqs.xlsx', 'prereqs')
student_grades = read_student_grades_excel('student_grades.xlsx', 'student_grades')

print(prereqs)
print(student_grades)

for course in prereqs.keys():
    print(course)
    eligible = is_eligible_for_course(course, prereqs, student_grades)
    print(f"Eligible for {course}: {'YES' if eligible else 'NO'}")

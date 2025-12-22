import re
import json
from typing import List, Tuple, Dict, Optional
import fitz  # PyMuPDF
from fastapi import UploadFile,File
import pandas as pd
import shutil
import os
import uuid
from datetime import datetime, timedelta
import math
from fastapi.responses import JSONResponse
from MultiplePrerequisites import student_grades,is_eligible_for_course
#####******courses_dict is not a dictionary it is a list of tuples
# Load CSV files

def sanitize_value(value):
    """Convert NaN, inf, -inf, or empty strings to None."""
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        else:
            return None
    if value in ("", " ", None, "nan", "NaN"):
        return None
    return value

def course_active(result):
    course_crn =[]
    multiple_courses_crns=[]
    for course,course_details in result.items():
        if "credits required from" not in course:
            for crn, crn_details in course_details.items():
                if crn_details['active_ind']=='I' or crn_details['active_ind']=='C':
                    course_crn.append(crn)
            for item in course_crn:
                del course_details[crn]
        # if "credits required from" in course:
        #     for course_num,details in course_details.items():
        #         for crn,crn_details in details.items():
        #             if crn_details['active_ind']=='I' or crn_details['active_ind']=='C':
        #                 del details[crn]    
    return result




course_list_path = "/home/bmt.lamar.edu/mpolineni/Latest_Class_Schedule.csv"     #"/home/bmt.lamar.edu/mpolineni/Latest_Class_Schedule.csv"   
course_prereq_path = '/home/bmt.lamar.edu/mpolineni/course_prerequisites.csv'  

# Load the course list dataframe
df_courses = pd.read_csv(course_list_path)

# Load the prerequisites dataframe
df_prereqs = pd.read_csv(course_prereq_path)


# def create_course_dictionary_from_df(df):
#     course_dict = {}
#     for _, row in df.iterrows():
#         course_dict[row['Subject']+" "+str(row['Course'])] = {
#             'course_title': row['Section_Title'],
#             'semester_offered': row['Term'],
#             'part_of_term':row['Part_of_Term'],
#             'mode':row['SXRFIMODDesc'],
#         }
#     return course_dict

def create_course_dictionary_from_df(df):
    course_dict = []
    for _, row in df.iterrows():
        if row['Active_Ind'] =='I' or row['Active_Ind'] =='C' or row['Campus_Code']=='AP':
            continue
        course_dict.append((row['Subject']+" "+str(row['Course']),row['Section_Title'],row['Term'],row['Part_of_Term'],row['SXRFIMODDesc'],row['CRN'],row['Begin_Time'],row['End_Time'],row['Faculty'],row['Avalailable_Seat'],row['Active_Ind']))
    return course_dict


def prerequisite_course_dictionary_from_df(df):
    prereq_dict = {}
    for _, row in df.iterrows():
        # Get prerequisite and assign default if empty or NaN
        prereq = row["pre_requisite"]
        if not isinstance(prereq, str) or not prereq.strip():
            prereq = "No prerequisite"

        # Build the dictionary
        prereq_dict[row['course_number']] = {
            'course_title': row['course_name'],
            'prerequisites': prereq,
            'co_requisites': row['co_requisite'],
            'passing_grade': row['passing_grade'],
            'usually_offered_semester': row['usually_offered_semester'],
            'comments': row['comments']
        }
    return prereq_dict




courses_dict = create_course_dictionary_from_df(df_courses)
prereq_dict = prerequisite_course_dictionary_from_df(df_prereqs)

def prerequesites_dict():
    prerequisites={}
    for course,details in prereq_dict.items():
        prerequisites[course]=details["prerequisites"]
    return prerequisites




def replace_course_keys(result, prereq_course_count):
    new_result = {}

    for key, value in result.items():
        # ---------- Case 1: top-level course key ----------
        if key in prereq_course_count:
            prereq_list = ", ".join(prereq_course_count[key][1:])
            new_key = f"{key} (is prerequisite for {prereq_list})"
            new_result[new_key] = value
            continue

        # ---------- Case 2: section headers ----------
        if isinstance(value, dict):
            new_inner = {}

            for inner_key, inner_value in value.items():
                if inner_key in prereq_course_count:
                    prereq_list = ", ".join(prereq_course_count[inner_key][1:])
                    new_inner_key = (
                        f"{inner_key} (is prerequisite for {prereq_list})"
                    )
                    new_inner[new_inner_key] = inner_value
                else:
                    new_inner[inner_key] = inner_value

            new_result[key] = new_inner
        else:
            new_result[key] = value

    return new_result



def math_sections(semester):
    selected_codes = {"MATH 3370", "MATH 2414", "MATH 2318", "MATH 2413", "MATH 2311", "MATH 2312"}
    result = {}

    for code, name, course_semester, part_of_term, mode,crn,begin_time,end_time,faculty,available_seats,active_ind in courses_dict:
        # Match the desired course and semester
        if code in selected_codes and course_semester.replace(" ", "").lower() == semester:
            key = f"{code} {name}"  # e.g. "MATH 2311 Precalculus I (Parent)"
            
            # If key doesn't exist, create a new list
            if key not in result:
                result[key] = []
            
            # Append each CRN
            result[key].append(crn)
    return result


def multiple_sections(filtered_courses, semester):
    sections_dict = {}
    for course,details in filtered_courses.items():
        for code, name, course_semester, part_of_term, mode,crn,begin_time,end_time,faculty,available_seats,active_ind in courses_dict:
            if course == code and course_semester.replace(" ", "").lower() == semester.lower():
                if code not in sections_dict:
                    sections_dict[code] = {}  
                sections_dict[code][crn] = details
        # if "credits required from:" in course:
        #     for multiple_courses,course_details in details.items():
        #         for code, name, course_semester, part_of_term, mode, crn in courses_dict:
        #             if multiple_courses == code and course_semester.replace(" ", "").lower() == semester.lower(): 
        #                 if code not in sections_dict:
        #                     sections_dict[code] = {}  
        #                 sections_dict[code][crn] = {
        #                     'course_title': name,
        #                     'semester_offered': course_semester,
        #                     'part_of_term': part_of_term,
        #                     'mode': mode
        #                 }
    return sections_dict

def gropus_multiple_sections(filtered_courses,semester):
    sections_dict = {}
    for course,details in filtered_courses.items():
        if "credits required from:" in course:
            for multiple_courses,course_details in details.items():
                for code, name, course_semester, part_of_term, mode,crn,begin_time,end_time,faculty,available_seats,active_ind in courses_dict:
                    if multiple_courses == code and course_semester.replace(" ", "").lower() == semester.lower(): 
                        if code not in sections_dict:
                            sections_dict[code] = {}  
                        sections_dict[code][crn] = course_details
    return sections_dict


# Assume course_dict is defined globally (outside the function)
def get_selected_courses(course_keys,semester,filtered_courses):
    """
    Returns a dictionary of courses that match the given list of course keys.
    
    Parameters:
    course_keys (list): A list of course codes (e.g., ['COSC 1172', 'CPSC 4375'])

    Returns:
    dict: A new dictionary with only the selected courses
    """
    dicts={}
    for key in course_keys:
        for course,details in filtered_courses.items():
            if key==course:
                for code, name, course_semester, part_of_term, mode,crn,begin_time,end_time,faculty,available_seats,active_ind in courses_dict:
                    if key==code and course_semester.replace(" ", "").lower()==semester:
                        dicts[key]=details
    return dicts

# def filter_courses_by_semester(courses_dict, semester_input):
#     semester_input = semester_input.lower().strip()
#     if semester_input not in ['fall', 'spring']:
#         raise ValueError("Invalid input. Please enter 'fall' or 'spring'")
    
#     filtered_courses = {}
#     for course_code, details in courses_dict.items():
#         offered = (details.get('semester_offered') or '').lower()
#         if (semester_input == 'fall' and ('fall' in offered or 'fall/spring' in offered)) or \
#            (semester_input == 'spring' and ('spring' in offered or 'fall/spring' in offered)):
#             filtered_courses[course_code] = details
#     return filtered_courses


# ===============================
# PDF text extraction
# ===============================
def extract_text_from_path(pdf_path) -> str:
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

async def extract_text_from_pdf(file: UploadFile = File(...)):
    # Ensure it's a PDF
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are supported."}

    # Generate a unique temporary filename
    temp_filename = f"temp_{uuid.uuid4()}.pdf"

    # Save the uploaded file to disk
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Use your existing function
        extracted_text = extract_text_from_path(temp_filename)
    finally:
        # Clean up: delete temp file
        os.remove(temp_filename)

    return extracted_text



# ===============================
# STOP before "Fall Through" (and similar)
# ===============================
STOP_SECTION_PATTERNS = (
    r'^\s*Fall\s*Through\b.*$',     # "Fall Through", "Fall Through Courses"
    r'^\s*Fallthrough\b.*$',
    r'^\s*Excess\s+Credits\b.*$',   # optional alternate label
)

def cut_before_stop_section(text: str) -> str:
    """Return text up to (but excluding) the first stop-section header."""
    earliest = None
    for pat in STOP_SECTION_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            pos = m.start()
            earliest = pos if earliest is None else min(earliest, pos)
    return text if earliest is None else text[:earliest]


# ===============================
# Helpers / regexes
# ===============================
COURSE_RE = re.compile(r"\b([A-Z]{3,6})\s+([0-9]{3,4}[A-Z]?)\b")
TERM_RE = re.compile(r"\b((?:Spring|Summer|Fall|Winter|Intersession)(?:\s+[IVX]+)?\s+20\d{2}|\b(?:FA|SP|SU|WI)\s*20\d{2})\b", re.I)
CREDITS_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:Credits?|CR|HRS?)\b", re.I)

GRADE_PASSING = re.compile(r"\b(?:A|B|C|D)(?:[+-])?\b|\b(?:CR|P|S|TA|TB|TC|TR)\b", re.I)
GRADE_FAILLIKE = re.compile(r"\b(?:F|U|W|Q|AU|NR)\b", re.I)
GRADE_INPROG = re.compile(r"\b(?:IP|INPR)\b", re.I)
INPROG_TOKENS = re.compile(r"\b(?:in[-\s]?progress)\b", re.I)


# ===============================
# Robust completed course detector
# ===============================
def normalize_lines(text: str) -> List[str]:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"[ \t]+", " ", (raw or "")).strip()
        if line and not re.fullmatch(r"[-=]{6,}", line):
            lines.append(line)
    return lines

def infer_status_from_context(nearby_text: str, grade: Optional[str]) -> str:
    g = (grade or "").upper()
    if GRADE_INPROG.search(g) or INPROG_TOKENS.search(nearby_text):
        return "In-Progress"
    if GRADE_FAILLIKE.search(g):
        return "Not Completed"
    if GRADE_PASSING.search(g):
        return "Completed"
    return ""  # unknown

def extract_completed_courses_robust(text: str) -> List[Dict]:
    lines = normalize_lines(text)
    results: List[Dict] = []

    current_section = ""
    n = len(lines)
    i = 0

    def make_record(subject, number, window_lines, section, title_hint=""):
        joined = " | ".join(window_lines)
        title = title_hint.strip(" -:|")
        if not title:
            for ln in window_lines[:6]:
                if COURSE_RE.search(ln):
                    continue
                if CREDITS_RE.search(ln):
                    continue
                if (GRADE_PASSING.fullmatch(ln) or GRADE_FAILLIKE.fullmatch(ln) or
                        GRADE_INPROG.fullmatch(ln)):
                    continue
                if TERM_RE.search(ln):
                    continue
                if ln.lower().startswith("satisfied by:"):
                    continue
                if re.search(r"[A-Za-z]", ln):
                    title = ln.strip(" -:|")
                    break

        grade = ""
        for ln in window_lines[:6]:
            if GRADE_INPROG.fullmatch(ln):
                grade = ln.upper(); break
            if GRADE_FAILLIKE.fullmatch(ln):
                grade = ln.upper(); break
            if GRADE_PASSING.fullmatch(ln):
                grade = ln.upper(); break
        if not grade:
            gtok = (GRADE_PASSING.search(joined) or
                    GRADE_FAILLIKE.search(joined) or
                    GRADE_INPROG.search(joined))
            if gtok:
                grade = gtok.group(0).upper()

        credits = None
        ctok = CREDITS_RE.search(joined)
        if ctok:
            try:
                credits = float(ctok.group(1))
            except Exception:
                credits = None
        if credits is None:
            for ln in window_lines[:6]:
                if re.fullmatch(r"\d+(?:\.\d+)?", ln):
                    credits = float(ln)
                    break
            if credits is None:
                mhrs = re.search(r"\b(\d+(?:\.\d+)?)\s+Credit\s+Hours\b", joined, re.I)
                if mhrs:
                    credits = float(mhrs.group(1))

        term = ""
        tmk = TERM_RE.search(joined)
        if tmk:
            term = tmk.group(0)

        satisfied_by = any(ln.lower().startswith("satisfied by:") for ln in window_lines[:8])
        if satisfied_by and not grade:
            status = "Completed"
        else:
            status = infer_status_from_context(joined, grade)

        if status in ["Completed","In-Progress"]:
            return {
                "subject": subject,
                "number": number,
                "title": title,
                "grade": grade,
                "credits": credits,
                "term": term,
                "status": status,
                "section": section
            }
        return None

    header_re = re.compile(
        r"^(?:Block|Area|Requirement|Audit|Major|Minor|Core|General Education|Prerequisites|In[- ]Progress|Legend)\b.*$"
        r"|^.*\b(Requirements|Electives|Curriculum|Concentration)\b.*$",
        re.I
    )

    while i < n:
        line = lines[i]

        if header_re.match(line):
            current_section = line
            i += 1
            continue

        mhrs = re.search(r"\b(\d+(?:\.\d+)?)\s+Credit\s+Hours\b", line, re.I)
        if mhrs:
            after = line[mhrs.end():]
            code_same = COURSE_RE.search(after)
            if code_same:
                subject, number = code_same.group(1), code_same.group(2)
                window = lines[max(0, i): min(n, i+8)]
                rec = make_record(subject, number, window, current_section,
                                  title_hint=after[code_same.end()-code_same.start():])
                if rec:
                    results.append(rec)
                i += 1
                continue
            else:
                look_max = min(n, i+6)
                found = False
                for j in range(i+1, look_max):
                    mcode = COURSE_RE.search(lines[j])
                    if mcode:
                        subject, number = mcode.group(1), mcode.group(2)
                        window = lines[i: min(n, j+6)]
                        tail = lines[j][mcode.end():]
                        rec = make_record(subject, number, window, current_section, title_hint=tail)
                        if rec:
                            results.append(rec)
                        i = j + 1
                        found = True
                        break
                if found:
                    continue
                i += 1
                continue

        mcode = COURSE_RE.search(line)
        if mcode:
            subject, number = mcode.group(1), mcode.group(2)
            window = lines[max(0, i-1): min(n, i+6)]
            tail = line[mcode.end():]
            rec = make_record(subject, number, window, current_section, title_hint=tail)
            if rec:
                results.append(rec)
            i += 1
            continue

        i += 1

    def richness(r):
        score = 0
        if r.get("grade"): score += 2
        if r.get("credits") is not None: score += 1
        if r.get("term"): score += 1
        if r.get("title"): score += 1
        return score

    best: Dict[Tuple[str, str], Dict] = {}
    for r in results:
        key = (r["subject"], r["number"])
        if key not in best or richness(r) > richness(best[key]):
            best[key] = r

    return list(best.values())


# ===============================
# Parse "X Credits in/from ... or ..." groups (credit value + fully-qualified list)
# ===============================
def parse_credit_or_block(block: str) -> Tuple[float, List[str]]:
    text = re.sub(r"[ \t]+", " ", block.strip())
    text = re.sub(r"\s*\n\s*", " ", text)
    m = re.search(r"(\d+(?:\.\d+)?)\s+Credits?\s+(?:in|from)\s+([A-Z]{4})\s?(\d{4})",
                  text, re.IGNORECASE)
    if not m:
        raise ValueError("No 'X Credits in/from SUBJ ####' header found.")
    credits = float(m.group(1))
    last_subject = m.group(2).upper()
    first_num = m.group(3)

    courses: List[str] = [f"{last_subject} {first_num}"]
    remainder = text[m.end():]
    token_re = re.compile(r"([A-Z]{4})\s?(\d{4})|\b(\d{4})\b")
    for t in token_re.finditer(remainder):
        subj_full, num_full, num_bare = t.groups()
        if num_full:
            last_subject = subj_full.upper()
            courses.append(f"{last_subject} {num_full}")
        elif num_bare and last_subject:
            courses.append(f"{last_subject} {num_bare}")

    seen, out = set(), []
    for c in courses:
        if c not in seen:
            seen.add(c); out.append(c)
    return credits, out

def extract_needed_or_groups_with_credits(text: str) -> List[Tuple[float, List[str]]]:
    lines = text.splitlines()
    groups: List[Tuple[float, List[str]]] = []
    in_needed_block = False
    current_block: List[str] = []

    def flush():
        nonlocal current_block
        if not current_block:
            return
        block_txt = "\n".join(current_block).strip()
        if re.search(r"^\s*\d+(?:\.\d+)?\s+Credits?\s+(?:in|from)\s+[A-Z]{4}\s?\d{4}",
                     block_txt, re.IGNORECASE | re.MULTILINE):
            try:
                groups.append(parse_credit_or_block(block_txt))
            except Exception:
                pass
        current_block = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.lower().startswith("still needed:"):
            flush()
            in_needed_block = True
            continue
        if not in_needed_block:
            continue
        if re.match(r"^\d+(?:\.\d+)?\s+Credits?\s+(?:in|from)\s+[A-Z]{4}\s?\d{4}", line, re.IGNORECASE):
            flush()
            current_block = [line]
            continue
        if current_block:
            if re.search(r"\bor\b", line, re.IGNORECASE) or \
               re.search(r"^[A-Z]{4}\s?\d{4}$", line) or \
               re.search(r"\b\d{4}\b", line):
                current_block.append(line)
                continue
            else:
                flush()
                continue
    flush()
    return groups


def prerequisite_course_dictionary(json_data):
    """
    Creates a dictionary containing only courses that have prerequisites,
    with course codes as keys and course details as values.
    
    Args:
        json_data: The loaded JSON data
        
    Returns:
        A dictionary with course codes as keys and course details as values
        (only includes courses that have prerequisites)
    """
    course_dict = {}
    
    # Iterate through all bundles and courses
    for bundle in json_data['bundles_list']:
        if 'courses' in bundle:
            for course in bundle['courses']:
                # Check for prerequisites (handling different key spellings)
                prereq_keys = ['Pre-requisites', 'pre-requisites', 'Prerequisites', 'prerequisites']
                prerequisites = None
                
                for key in prereq_keys:
                    if key in course:
                        prerequisites = course[key]
                        break
                
                # Only add courses that have prerequisites
                if prerequisites:
                    course_details = {
                        'course_title': course.get('course_title') or course.get('course_name'),
                        'credit_hours': course.get('credit_hours'),
                        'semester_offered': course.get('semester_offered'),
                        'prerequisites': prerequisites,
                        'bundle_id': bundle.get('bundle_id'),
                        'bundle_name': bundle.get('bundle_name')
                    }
                    course_dict[course['course_code']] = course_details
    
    return course_dict


def create_course_dictionary(json_data):
    """
    Creates a dictionary of courses with course codes as keys and course details as values.
    
    Args:
        json_data: The loaded JSON data
        
    Returns:
        A dictionary with course codes as keys and course details as values
    """
    course_dict = {}
    
    # Iterate through all bundles and courses
    for bundle in json_data['bundles_list']:
        if 'courses' in bundle:
            for course in bundle['courses']:
                # Standardize the course details structure
                course_details = {
                    'course_title': course.get('course_title') or course.get('course_name'),
                    'credit_hours': course.get('credit_hours'),
                    'semester_offered': course.get('semester_offered'),
                    'prerequisites': None
                }
                
                # Handle prerequisites (check for different key spellings)
                prereq_keys = ['Pre-requisites', 'pre-requisites', 'Prerequisites', 'prerequisites']
                for key in prereq_keys:
                    if key in course:
                        course_details['prerequisites'] = course[key]
                        break
                
                # Add to dictionary with course code as key
                course_dict[course['course_code']] = course_details
    
    return course_dict

# def filter_courses_by_semester(courses_dict, semester_input, course_code_list):
#     """
#     Filters courses based on a provided list of course codes and semester input.

#     Args:
#         courses_dict (dict): Dictionary of all courses (from create_course_dictionary)
#         semester_input (str): User input ('fall' or 'spring')
#         course_code_list (list): List of course codes to filter from the dictionary

#     Returns:
#         dict: Filtered dictionary {course_code: course_details}
#     """
#     # Normalize user input
#     semester_input = semester_input.lower().strip()

#     # Validate input
#     if semester_input not in ['fall', 'spring']:
#         raise ValueError("Invalid input. Please enter 'fall' or 'spring'")

#     filtered_courses = {}

#     for course_code in course_code_list:
#         # Ensure course_code exists in dictionary
#         if course_code in courses_dict:
#             course_details = courses_dict[course_code]
#             if 'semester_offered' in course_details:
#                 offered = course_details['semester_offered'].replace(" ","").lower()

#                 if (semester_input == 'fall' and ('fall2025' in offered or 'fall2026' in offered)) or \
#                    (semester_input == 'spring' and ('spring2025' in offered or 'spring2026' in offered)):
#                     filtered_courses[course_code] = course_details.copy()

#     return filtered_courses


def filter_courses_by_semester(courses_dict, semester_input, course_code_list):
    """
    Filters courses based on a provided list of course codes and semester input.

    Args:
        courses_dict (dict): Dictionary of all courses (from create_course_dictionary)
        semester_input (str): User input like 'fall 2025', 'spring2026', etc.
        course_code_list (list): List of course codes to filter from the dictionary

    Returns:
        dict: Filtered dictionary {course_code: course_details}
    """
    semester_input = semester_input.strip().lower().replace(" ", "")

    match = re.match(r'(fall|spring|summer)', semester_input)
    if not match:
        raise ValueError("❌ Invalid semester. Use formats like 'Fall 2025', 'Spring2026', etc.")

    semester = match.group(1)

    year_match = re.search(r'(\d{4})', semester_input)
    if not year_match:
        raise ValueError("❌ Year is required. Please include a 4-digit year (e.g., 'Fall 2025').")

    year = year_match.group(1)

    filtered_courses = {}

    for course_code in course_code_list:
        for code, name, course_semester, part_of_term, mode,crn,begin_time,end_time,faculty,available_seats,active_ind in courses_dict:
            if course_code ==code:
                course_details = {'course_title':name,'semester_offered':course_semester,'part_of_term':part_of_term,'mode':mode,'begin_time':sanitize_value(begin_time),'end_time':sanitize_value(end_time),'faculty':sanitize_value(faculty),'available_seats':sanitize_value(available_seats),'active_ind':active_ind}
                if 'semester_offered' in course_details:
                    offered = course_details['semester_offered'].replace(" ", "").lower()

                    if f"{semester}{year}" in offered:
                        filtered_courses[course_code] = course_details.copy()

    return filtered_courses,f"{semester}{year}"



def mathCourses(completed_courses,incomplete_courses,non_elegible_courses):
    for c in completed_courses:
        if "MATH 2414" == (c['subject'] + " " + c['number']):
            for i in incomplete_courses:
                for i_c in i[1]:
                    if i_c=="MATH 2413" or i_c=="MATH 2312" or i_c=="MATH 2311":
                        non_elegible_courses[i_c]="Completed Upper Level MATH Courses"
                        incomplete_courses.remove(i)
        if "MATH 2413" == (c['subject'] + " " + c['number']):
            for i in incomplete_courses:
                for i_c in i[1]:
                    if i_c=="MATH 2312" or i_c=="MATH 2311":
                        non_elegible_courses[i_c]="Completed Upper Level MATH Courses"
                        incomplete_courses.remove(i)
        if "MATH 2312" == (c['subject'] + " " + c['number']):
            for i in incomplete_courses:
                for i_c in i[1]:
                    if i_c=="MATH 2311":
                        non_elegible_courses[i_c]="Completed Upper Level MATH Courses"
                        incomplete_courses.remove(i)
    return completed_courses, incomplete_courses


def multipleCourses(completed_courses,incomplete_courses,filtered_courses,semester):
    completely_elegible_courses={}
    # for tuples in incomplete_courses:
    #     if len(tuples[1]) > 1:
    #         for course in tuples[1]:
    #             if any(course == f"{n['subject']} {n['number']}" for n in completed_courses):
    #                 tuples[1].remove(course)   
    for index, tuples in enumerate(incomplete_courses, 1):
        if (len(tuples[1])>1):
            tuples = (tuples[0], [item for item in tuples[1] if item in filtered_courses.keys()])
            completely_elegible_courses[f"{index}. {tuples[0]} credits required from: "]=get_selected_courses(tuples[1],semester,filtered_courses)
    for tuples in incomplete_courses:
        if len(tuples[1])>1:
            for key in tuples[1]:
                if key in filtered_courses:
                    del filtered_courses[key]
    return completely_elegible_courses


def filter_courses_by_prereq(courses_list, course_dict):
    matched_courses = {}
    # Create a set of valid numbers for fast lookup
    valid_numbers = {course["number"] for course in courses_list}

    for course_code, details in course_dict.items():
        prereq_text = details.get("Pre-requisites", "")
        match = re.search(r"\b\d{4}\b", prereq_text)  # Find 4-digit number
        if match:
            prereq_number = match.group()
            if prereq_number in valid_numbers:
                matched_courses[course_code] = details

    return matched_courses

def final_courses_dictionary(filtered_courses,multiple_courses):
    for course_code,course_details in multiple_courses.items():
        filtered_courses[course_code]=course_details
    return filtered_courses

def groups_final_courses_dictionary(groups,multiple_courses):
    for course_code,course_details in multiple_courses.items():
        for course in groups:
            if course==course_code:
                groups[course_code]=course_details
    return groups

def degree_process_time(text):
    pattern = r"\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+(AM|PM)"
    degree_date_time = re.search(pattern, text)
    date_str=degree_date_time.group().replace("  ", " ")
    dt_format = "%m/%d/%Y %I:%M %p"
    text_datetime = datetime.strptime(date_str, dt_format)

    # Step 3: Get current datetime
    current_datetime = datetime.now()

    # Step 4: Calculate time difference
    time_difference = current_datetime - text_datetime
    hours_diff = time_difference.total_seconds() / 3600  # convert to hours

    print(f"⏳ Time difference: {hours_diff:.2f} hours")

    # Step 5: Check if more than 48 hours
    if hours_diff > 48:
        raise Exception("Degree audit not up to date (older than 48 hours).")



def pre_req_comments(filtered_courses):
    for key in filtered_courses:
        for course in prereq_dict:
            if key == course:
                comments = prereq_dict[key].get("comments", "-")
                usually_offered = prereq_dict[key].get("usually_offered_semester", "-")
                # Replace NaN values with "-"
                if isinstance(comments, float) and math.isnan(comments):
                    comments = "-"
                if isinstance(usually_offered, float) and math.isnan(usually_offered):
                    usually_offered = "-"

                filtered_courses[key]["comments"] = comments
                filtered_courses[key]["usually_offered_semester"] = usually_offered
    return filtered_courses


async def main(path):
    pdf_file = path  # <-- adjust path
    print("🔄 Reading DegreeWorks PDF...")
    text =await extract_text_from_pdf(pdf_file)

    text = cut_before_stop_section(text)


    text=text.replace("1 Class", "3 Credits")
    # degree_process_time(text)

  
    completed = extract_completed_courses_robust(text)

    # Incomplete groups: list of tuples (credits_required, list_of_courses)
    groups = extract_needed_or_groups_with_credits(text)
    return completed, groups


    # Now you have:
    # completed_courses -> List[Dict] with full course details      
    # incomplete_groups -> List[Tuple[float, List[str]]] with credits + courses

# if __name__ == "__main__":
async def course_suggestion(degree_audit,term):
    # Your main PDF parsing remains same
    completed_courses, incomplete_groups = await main(degree_audit) 
    non_elegible_courses = {}
    completed_courses,incomplete_groups=mathCourses(completed_courses,incomplete_groups,non_elegible_courses)

    semester = term

    #for testing unelegible courses
    # completed_courses=[{'subject': 'ENGL', 'number': '1301', 'title': 'COMPOSITION I', 'grade': 'TA', 'credits': 3.0, 'term': 'Fall 2016', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'FREN', 'number': '1311', 'title': 'Beginning French I', 'grade': 'B', 'credits': 3.0, 'term': 'Fall 2017', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'MATH', 'number': '2413', 'title': 'Calculus & Analytical Geom I', 'grade': 'A', 'credits': 1.0, 'term': 'Summer 2023', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'BIOL', 'number': '1407', 'title': 'Credits', 'grade': 'C', 'credits': 4.0, 'term': 'Fall 2017', 'status': 'Completed', 'section': 'Core Curriculum if NOT required for the degree.'}, {'subject': 'CHEM', 'number': '1311', 'title': 'Barrera Cribas, Francisco - *****4152', 'grade': 'C', 'credits': 3.0, 'term': 'Fall 2016', 'status': 'Completed', 'section': 'Core Curriculum if NOT required for the degree.'}, {'subject': 'CHEM', 'number': '1111', 'title': 'General Chemistry I Laboratory', 'grade': 'B', 'credits': 4.0, 'term': 'Fall 2016', 'status': 'Completed', 'section': 'Core Curriculum if NOT required for the degree.'}, {'subject': 'ENGL', 'number': '2331', 'title': 'Worl Literature', 'grade': 'TB', 'credits': 3.0, 'term': 'Spring 2017', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'ARTS', 'number': '1301', 'title': 'Art Appreciation', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2016', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'HIST', 'number': '1301', 'title': 'U S HISTORY I-1763-1877', 'grade': 'TB', 'credits': 6.0, 'term': 'Spring 2017', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'HIS', 'number': '1763', 'title': '1877 - Lamar State College-Port Arthu', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2023', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'HIST', 'number': '1302', 'title': '', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2023', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'SINCE', 'number': '1877', 'title': '', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2023', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'POLS', 'number': '2301', 'title': 'AM GOVT I', 'grade': 'TB', 'credits': 6.0, 'term': 'Spring 2017', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'POLS', 'number': '2302', 'title': 'GOVT2306 - INT TO STATE GOVT - Lamar State College-Port Arthu', 'grade': 'TB', 'credits': 3.0, 'term': 'Fall 2016', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'ECON', 'number': '2302', 'title': 'PRIN OF ECONOMICS II (MICRO)', 'grade': 'TA', 'credits': 3.0, 'term': 'Summer 2017', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'ENGL', 'number': '1302', 'title': 'COMPOSITION II', 'grade': 'TB', 'credits': 3.0, 'term': 'Summer 2017', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'COMM', 'number': '1315', 'title': 'PUBLIC SPEAKING I', 'grade': 'TB', 'credits': 1.0, 'term': 'Spring 2018', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'TRNS', 'number': '1000', 'title': 'SPCH1315 - PUBLIC SPEAKING - Lamar State College-Port Arthu', 'grade': 'TA', 'credits': 1100.0, 'term': '', 'status': 'Completed', 'section': 'required for Core Curriculum if NOT required for the degree.'}, {'subject': 'MATH', 'number': '2414', 'title': 'Mathematic Prerequisites for Computer Science', 'grade': 'C', 'credits': 4.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'Prerequisites'}, {'subject': 'COSC', 'number': '1336', 'title': 'Fundamentals I', 'grade': 'A', 'credits': 3.0, 'term': 'Summer 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1172', 'title': 'Still needed', 'grade': 'A', 'credits': 1.0, 'term': '', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1173', 'title': 'Programming Lab I', 'grade': 'A', 'credits': 1.0, 'term': 'Summer 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1174', 'title': 'Programming Lab II', 'grade': 'A', 'credits': 1.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1337', 'title': 'Fundamentals II', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'},{'subject': 'COSC', 'number': '2325', 'title': 'Computer Organization', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '2375', 'title': 'Discrete Structures', 'grade': 'A', 'credits': 3.0, 'term': 'Spring 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '3302', 'title': 'Intro to Computer Theory', 'grade': 'A', 'credits': 3.0, 'term': 'Spring 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '4272', 'title': 'Still needed', 'grade': 'B', 'credits': 2.0, 'term': '', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '3308', 'title': 'Programming Language', 'grade': 'B', 'credits': 3.0, 'term': 'Fall 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '3325', 'title': 'Computer Law & Ethics', 'grade': 'A', 'credits': 3.0, 'term': 'Spring 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '4302', 'title': 'Operating Systems', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '4310', 'title': 'Intro to Computer Architecture', 'grade': 'B', 'credits': 3.0, 'term': 'Fall 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'CPSC', 'number': '4317', 'title': 'Still needed', 'grade': 'B', 'credits': 3.0, 'term': '', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'CPSC', 'number': '4340', 'title': 'Database Design', 'grade': 'B', 'credits': 3.0, 'term': 'Fall 2025', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'CPSC', 'number': '4360', 'title': 'Software Engineering', 'grade': 'A', 'credits': 3.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'CPSC', 'number': '4363', 'title': 'Secure Software Engineering or Cybersecurity', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '4333', 'title': 'Still needed', 'grade': 'B', 'credits': 3.0, 'term': '', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'MATH', 'number': '2318', 'title': 'Linear Algebra', 'grade': 'B', 'credits': 3.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'MATH REQUIREMENTS'}, {'subject': 'COSC', 'number': '3306', 'title': 'COSC/CPSC/ELEN Upper-Level Elective', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'MATH REQUIREMENTS'}, {'subject': 'COSC', 'number': '4301', 'title': 'ST: Cloud Computing', 'grade': 'A', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'MATH REQUIREMENTS'}, {'subject': 'CPSC', 'number': '4364', 'title': 'Barrera Cribas, Francisco - *****4152', 'grade': 'C', 'credits': 3.0, 'term': 'Summer 2025', 'status': 'Completed', 'section': 'MATH REQUIREMENTS'}, {'subject': 'ARTS', 'number': '2316', 'title': 'Academic Elective', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2017', 'status': 'Completed', 'section': 'MATH REQUIREMENTS'}]
    # incomplete_groups=[(1.0, ['COSC 1172']), (3.0, ['COSC 3304']),(3.0, ['COSC 2336']),(2.0, ['COSC 4272']), (3.0, ['CPSC 4317']), (3.0, ['COSC 4333']), (3.0, ['MATH 3370']), (3.0, ['COSC 3306', 'COSC 4301', 'COSC 4307', 'COSC 4309', 'COSC 4319', 'COSC 4322', 'COSC 4324', 'COSC 4345', 'CPSC 3316', 'CPSC 4315', 'CPSC 4316', 'CPSC 4361', 'CPSC 4320', 'CPSC 4330', 'CPSC 4370', 'ELEN 3381', 'ELEN 4486', 'ELEN 4387', 'ELEN 4304'])]

    #for testing Prereq-course priority
    # completed_courses = [{'subject': 'ENGL', 'number': '1301', 'title': 'Composition I', 'grade': 'TA', 'credits': 6.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'SPAN', 'number': '1311', 'title': '1', 'grade': 'TA', 'credits': 3.0, 'term': 'Summer 2024', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'MATH', 'number': '2413', 'title': 'CALC & ANALY GEOM I', 'grade': '', 'credits': 3.0, 'term': 'Summer 2025', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'PHYS', 'number': '2425', 'title': 'University Physics I', 'grade': 'TA', 'credits': 8.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'BIOL', 'number': '1406', 'title': 'or 1407', 'grade': 'A', 'credits': 4.0, 'term': '', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'PHIL', 'number': '1370', 'title': 'Hours', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'MUSI', 'number': '1306', 'title': 'MUSIC APPRECIATION', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'HIST', 'number': '1301', 'title': 'US History I 1763-1877', 'grade': 'TA', 'credits': 6.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'HIST', 'number': '1302', 'title': 'HIST1301 - UNITED STATES HISTORY I - Austin Community College', 'grade': 'TA', 'credits': 3.0, 'term': 'Fall 2024', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'POLS', 'number': '2301', 'title': 'AMERICAN GOVT I', 'grade': 'TA', 'credits': 6.0, 'term': 'Summer 2024', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'POLS', 'number': '2302', 'title': 'GOVT2306 - TX & LOCAL GOV - Austin Community College', 'grade': 'TA', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'PSYC', 'number': '2301', 'title': 'Hours', 'grade': 'TA', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'MATH', 'number': '2415', 'title': '090 Component Area Option', 'grade': 'TA', 'credits': 4.0, 'term': 'Spring 2024', 'status': 'Completed', 'section': 'If a student took a course that was part of the Texas Core Curriculum at the sending institution, Lamar University will recognize it here as core based on the'}, {'subject': 'MATH', 'number': '2312', 'title': 'Precalculus II', 'grade': '', 'credits': 3.0, 'term': 'Summer 2025', 'status': 'Completed', 'section': 'Prerequisites'}, {'subject': 'MATH', 'number': '2414', 'title': 'Calculus II', 'grade': '', 'credits': 4.0, 'term': 'Summer 2025', 'status': 'Completed', 'section': 'Prerequisites'}, {'subject': 'COSC', 'number': '1336', 'title': 'Programming Fund I', 'grade': 'TA', 'credits': 3.0, 'term': 'Fall 2023', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1174', 'title': 'Still needed', 'grade': 'TA', 'credits': 1.0, 'term': '', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}, {'subject': 'COSC', 'number': '1337', 'title': 'Programming Fund II', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2024', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'},{'subject': 'COSC', 'number': '2325', 'title': 'Computer Organization', 'grade': 'TA', 'credits': 3.0, 'term': 'Spring 2025', 'status': 'Completed', 'section': 'Unmet conditions for this set of requirements:'}]
    # incomplete_groups = [(3.0, ['PHYS 1370']), (1.0, ['COSC 1172']), (1.0, ['COSC 1173']),(3.0,['COSC 2336']), (1.0, ['COSC 1174']), (3.0, ['COSC 2375']), (3.0, ['COSC 3302']), (3.0, ['COSC 3304']), (2.0, ['COSC 4272']), (3.0, ['COSC 3308']), (3.0, ['COSC 3325']), (3.0, ['COSC 4310']), (3.0, ['CPSC 4317']), (3.0, ['CPSC 4340']), (3.0, ['CPSC 4360']), (3.0, ['CPSC 4361', 'CPSC 4363', 'COSC 4345']), (3.0, ['COSC 4333']), (3.0, ['MATH 2318']), (3.0, ['MATH 3370']), (6.0, ['COSC 4301', 'COSC 4319','COSC 4345', 'CPSC 4315', 'CPSC 4330', 'CPSC 4370', 'CPSC 4375', 'ELEN 3381', 'ELEN 4486', 'ELEN 4387', 'ELEN 4304']), (6.0, ['COSC 3306', 'COSC 4301', 'COSC 4319', 'COSC 4345', 'CPSC 4315', 'CPSC 4361', 'CPSC 4330', 'CPSC 4363', 'CPSC 4370', 'CPSC 4375'])]
    # incomplete_groups=[(3.0, ['PHYS 1370']), (1.0, ['COSC 1172']), (1.0, ['COSC 1173']), (1.0, ['COSC 1174']), (3.0, ['COSC 2375']),(3.0, ['COSC 2336']), (3.0, ['COSC 3302']), (3.0, ['COSC 3308']), (3.0, ['COSC 3325']), (3.0, ['COSC 4310']), (3.0, ['CPSC 4361', 'CPSC 4363', 'COSC 4345']), (3.0, ['COSC 4333']), (3.0, ['MATH 2318']), (3.0, ['MATH 3370']), (6.0, ['COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4370', 'CPSC 4375', 'ELEN 3381', 'ELEN 4486', 'ELEN 4387', 'ELEN 4304']), (6.0, ['COSC 3306', 'COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4361', 'CPSC 4363', 'CPSC 4370', 'CPSC 4375'])]
    # incomplete_groups=[(3.0, ['PHYS 1370']), (1.0, ['COSC 1172']), (1.0, ['COSC 1173']), (1.0, ['COSC 1174']), (3.0, ['COSC 2375']),(3.0, ['COSC 2336']), (3.0, ['COSC 3302']), (3.0, ['COSC 3308']), (3.0, ['COSC 3325']), (3.0, ['COSC 4310']), (3.0, ['CPSC 4361', 'CPSC 4363', 'COSC 4345']), (3.0, ['COSC 4333']), (3.0, ['MATH 2318']), (3.0, ['MATH 3370']), (6.0, ['COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4375', 'ELEN 3381', 'ELEN 4486', 'ELEN 4387', 'ELEN 4304']), (6.0, ['COSC 3306', 'COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4361', 'CPSC 4363',  'CPSC 4375'])]
    # incomplete_groups=[(3.0, ['PHYS 1370']), (1.0, ['COSC 1172']), (1.0, ['COSC 1173']), (1.0, ['COSC 1174']),(3.0, ['COSC 2336']), (3.0, ['COSC 3302']), (3.0, ['COSC 3308']), (3.0, ['COSC 3325']), (3.0, ['COSC 4310']), (3.0, ['CPSC 4361', 'CPSC 4363', 'COSC 4345']), (3.0, ['COSC 4333']), (3.0, ['MATH 2318']), (3.0, ['MATH 3370']), (6.0, ['COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4375', 'ELEN 3381', 'ELEN 4486', 'ELEN 4387', 'ELEN 4304']), (6.0, ['COSC 3306', 'COSC 4301', 'COSC 4324', 'COSC 4345', 'CPSC 4361', 'CPSC 4363',  'CPSC 4375'])]
    
    completed_course_codes = {f"{c['subject']} {c['number']}" for c in completed_courses}
    elegible_prereq_courses=[]
    for credits, course_list in incomplete_groups:
        for course in course_list:
            if re.match(r"[A-Z]{4} \d{4}", course):
                elegible_prereq_courses.append(course)
                # prereq_info = prereq_dict.get(course)
                # if prereq_info:
                #     prereq_str = prereq_info.get('prerequisites', '')
                #     # Extract all course codes from prereq_str (could be multiple)
                #     prereq_courses = re.findall(r"[A-Z]{4} \d{4}", prereq_str)
                #     # Check if all prereqs are in completed courses
                #     if all(pr in completed_course_codes for pr in prereq_courses):
                #         elegible_prereq_courses.append(course)
                # else:
                #     elegible_prereq_courses.append(course)
    # Filter courses offered in the input semester
    try:
        filtered_courses,semester = filter_courses_by_semester(courses_dict, semester,elegible_prereq_courses)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"message": str(e)})



    for course in elegible_prereq_courses:
        if course in filtered_courses:
            continue
        else:
            non_elegible_courses[course]="S"

    filtered_courses=pre_req_comments(filtered_courses)
    multiple_courses_dict=multipleCourses(completed_courses,incomplete_groups,filtered_courses,semester)
    final_courses_dictionary(filtered_courses,multiple_courses_dict)
    sections=multiple_sections(filtered_courses,semester)
    groups_sections=gropus_multiple_sections(filtered_courses,semester)
    for course, course_details in filtered_courses.items():
        if "credits required from:" in course:
            filtered_courses[course]=groups_final_courses_dictionary(course_details,groups_sections)
    result=final_courses_dictionary(filtered_courses,sections)
    grades= student_grades(completed_courses)
    multiple_prereqs=prerequesites_dict()

    prereq_course_count={}  


    for course,prereq_courses in multiple_prereqs.items():
        if "and" in prereq_courses or "or" in prereq_courses or "=" in prereq_courses:
            eligible = is_eligible_for_course(course, multiple_prereqs,grades)
            if eligible:
                continue
            elif course in result:
                non_elegible_courses[course]="P"
                del result[course]


            for courses in result:
                if "credits required from" in courses:
                    if course in result[courses]:
                        non_elegible_courses[course]="P"
                        del result[courses][course]
            

            #Prereqs_count

            for credits,course_codes in incomplete_groups:
                if course in course_codes: 
                    if "and" in prereq_courses:                                 
                        parts=prereq_courses.split("and")
                        for part in parts:
                            extract_course=re.findall(r'[A-Z]{4}\s\d{4}', part)
                            if extract_course[0] in prereq_course_count:
                                if course not in prereq_course_count[extract_course[0]]:
                                    prereq_course_count[extract_course[0]][0]+=1
                                    prereq_course_count[extract_course[0]].append(course)
                                continue
                            else:
                                prereq_course_count[extract_course[0]]=[1]
                                prereq_course_count[extract_course[0]].append(course)
                                continue


                    if "or" in prereq_courses:
                        orParts=prereq_courses.split("or")
                        for orPart in orParts:
                            or_extract_course=re.findall(r'[A-Z]{4}\s\d{4}', orPart)
                            if or_extract_course[0] in prereq_course_count:
                                if course not in prereq_course_count[or_extract_course[0]]:
                                    prereq_course_count[or_extract_course[0]][0]+=1
                                    prereq_course_count[or_extract_course[0]].append(course)
                                continue
                            else:
                                prereq_course_count[or_extract_course[0]] = [1]
                                prereq_course_count[or_extract_course[0]].append(course)
                                continue

                    if "=" in prereq_courses and 'or' not in prereq_courses and "and" not in prereq_courses:
                        single_extract_course = extract_course=re.findall(r'[A-Z]{4}\s\d{4}', prereq_courses)[0]
                        if single_extract_course in prereq_course_count:
                            if course not in prereq_course_count[single_extract_course]:
                                prereq_course_count[single_extract_course][0]+=1
                                prereq_course_count[single_extract_course].append(course)
                            continue
                        else:
                            prereq_course_count[single_extract_course]=[1]
                            prereq_course_count[single_extract_course].append(course)   


    result["Non-Eligible-Courses"]=non_elegible_courses 
    
    return replace_course_keys(result,prereq_course_count)




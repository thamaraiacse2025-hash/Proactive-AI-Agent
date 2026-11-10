import sqlite3
from pathlib import Path

# Find the project folder and database
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "internships.db"

# Descriptions for the six jobs that were missing descriptions.
# The first three are based on the descriptions you provided.
# Edwards, Codentix and Netlyft are prepared summaries/drafts,
# not claimed to be their exact original wording.

descriptions = [
    {
        "company": "Bluebex",
        "job_title": "Software Engineer Intern (Mobile & Web)",
        "description": """
Company Description

Bluebex builds technology that helps organizations shape the future by
modernizing their digital capabilities. The company partners with clients
to update legacy systems, redesign core processes, and create engaging,
user-centered experiences. Bluebex focuses on innovative digital solutions
that deliver practical value and long-term impact. Team members have
opportunities to work on modern tools and frameworks while contributing
to products that improve how people interact with technology.

Role Description

The Software Engineer Intern (Mobile & Web) role at Bluebex is a full-time
hybrid position based in Kochi, with flexibility for some work from home.
Interns collaborate with engineers and designers to develop, test, and
maintain web and mobile application features. Day-to-day responsibilities
include writing clean, efficient code, assisting with back-end services
and APIs, debugging issues, and participating in code reviews. The role
also involves researching new tools and frameworks, documenting technical
work, and supporting the team in delivering high-quality, user-focused
digital experiences.

Qualifications

- Strong foundation in Computer Science and Software Development principles.
- Hands-on experience or coursework in Programming and Object-Oriented
  Programming (OOP).
- Exposure to Back-End Web Development, including working with APIs and
  server-side logic.
- Familiarity with web and/or mobile technologies, such as JavaScript
  frameworks or native/cross-platform mobile tools, is an advantage.
- Ability to learn quickly, follow best coding practices, and work
  collaboratively in a team environment.
- Good problem-solving skills and attention to detail in debugging
  and testing software.
- Currently pursuing or recently completed a degree in Computer Science,
  Engineering, or a related technical field.
- Effective written and verbal communication skills in English.
"""
    },
    {
        "company": "Electronic Arts (EA)",
        "job_title": "JAVA Software Engineer Intern",
        "description": """
Description & Requirements

Electronic Arts creates next-level entertainment experiences that inspire
players and fans around the world. Here, everyone is part of the story.
Part of a community that connects across the globe. A place where creativity
thrives, new perspectives are invited, and ideas matter. A team where
everyone makes play happen.

EADP Java SE Intern

EA's Digital Platform (EADP) organization is responsible for driving
critical technology decisions and investments for EA on a global scale,
across all divisions and studio teams. Technology and engineering leadership
at EA is critical to making the industry's best games and services. The
EADP team provides cross-platform services that keep consumers connected
with games anytime, anywhere, with anyone.

As a Java software engineer intern, you will gain hands-on experience
working on a large gaming platform and learn how to design scalable,
high-performance software platforms alongside experienced developers.

Location: Hyderabad

Responsibilities

- Work with Product Managers, senior engineers and peers to understand
  requirements, prototype and build large-scale distributed applications.
- Build and deploy new microservices and enhance existing microservices.
- Focus on code quality, testability, maintainability and automated
  test coverage.
- Analyse and troubleshoot cloud-native applications relating to
  performance and scale.
- Implement observability, metrics, traces and telemetry to evaluate
  feature success.
- Prototype new technologies for specific use cases and validate them
  against success criteria.
- Communicate and coordinate with teams across different geographies.
- Communicate progress and issues during daily stand-ups.

Qualifications

- Bachelor's or master's degree in Computer/Software Engineering,
  Computer Science or a related discipline, or an equivalent combination
  of education.
- Foundation in Computer Science fundamentals, algorithms, design
  patterns, CI/CD processes and data structures.
- Object-oriented design and programming skills, with Java, Scala or
  related programming languages.
- Strong problem-solving abilities.
- Knowledge of SQL and NoSQL databases.
- Familiarity with cloud and cloud-native technologies.
- Experience with DevOps tools such as Docker.
- Understanding of large-scale, low-latency distributed systems.
- Experience with source-control tools such as Git.

About Electronic Arts

EA values adaptability, resilience, creativity and curiosity. It supports
learning, experimentation and professional growth. Its benefits may include
healthcare coverage, mental well-being support, retirement savings, paid
time off, family leaves and complimentary games, depending on local needs.

Electronic Arts is an equal opportunity employer and considers applicants
without discrimination on legally protected grounds. Workplace accommodations
are available for qualified applicants with disabilities as required by law.
"""
    },
    {
        "company": "Edwards Lifesciences",
        "job_title": "IT Internship Program (January - June 2027)",
        "description": """
Company Description

Edwards Lifesciences is a medical technology company focused on developing
technologies intended to improve patient outcomes.

Role Description

The IT Internship Program is based in Pune and runs from January to June
2027. It offers students an opportunity to gain practical experience through
technology projects. Depending on the assignment, interns may work in
software development, data analytics, artificial intelligence, automation,
cloud technologies or enterprise IT.

Responsibilities

- Assist with developing, testing, supporting and implementing technology
  solutions.
- Collaborate with business and IT teams to address practical challenges.
- Contribute to data analysis, reporting, automation and AI-related initiatives.
- Support software development, application enhancements and cloud projects.
- Document requirements, workflows, technical designs and project outcomes.
- Participate in testing, troubleshooting and continuous improvement.
- Present project updates and recommendations to relevant stakeholders.

Qualifications

- Pursuing a degree in Computer Science, IT, Software Engineering,
  Data Science, Information Systems, Engineering or a related field.
- Available for the full-time January-June 2027 internship.
- Good academic standing and interest in technology.
- Analytical thinking, problem-solving and communication skills.
- Ability to collaborate with a team and learn new technologies.

Preferred Skills

Python, SQL, data analytics, AI/ML, cloud technologies, software development,
business analysis, Power BI, data visualization, Git and CI/CD.

Note: This is a prepared summary based on the job posting, not its
word-for-word original description.
"""
    },
    {
        "company": "Google",
        "job_title": "Software Engineering Intern, Summer 2027",
        "description": """
Join us for a 10-12 week Summer Internship Program starting in May/June
2027. This program is designed to accelerate your personal and professional
growth while building a lasting community. As a Software Engineering Intern,
you will be a key player on a dynamic team, driving the development of
AI-integrated software and high-performance applications. Your primary
objective is to design, deploy, and maintain the end-to-end infrastructure
that sustains our large-scale systems. This is a unique opportunity to
contribute to Google's core needs while evolving your technical expertise
in a fast-paced, real-world environment.

Google's Software Engineers develop the next-generation technologies that
change how billions of users connect, explore, and interact with information
and one another. Our products need to handle information at a massive scale,
and extend well beyond web search. We need our engineers to be versatile,
display leadership qualities and be enthusiastic to take on new problems
across the full-stack as we continue to push technology forward.

Google is and always will be an engineering company. We hire people with a
broad set of technical skills who are ready to address some of technology's
greatest challenges and make an impact on millions, if not billions, of
users. At Google, engineers work on massive scalability and storage solutions,
large-scale applications and entirely new platforms for developers around
the world.

Responsibilities

- Foster a culture of productivity and innovation by actively supporting
  your peers and managers.
- Collaborate across teams to ensure the continued success and evolution
  of AI-driven software and large-scale systems.
- Develop scalable engineering solutions for Google products.
- Analyse information and evaluate results to choose the best solution
  to effectively solve issues.
- Apply knowledge gained in computer science courses to real-world challenges.

Google is an equal opportunity workplace and affirmative action employer.
It is committed to equal employment opportunity regardless of protected
characteristics. Applicants who require disability-related accommodation
can submit an accommodation request.
"""
    },
    {
        "company": "Codentix Tech LLP",
        "job_title": "Full Stack Web Developer Intern PHP (NON PAID)",
        "description": """
Company Description

Codentix Tech LLP provides digital technology services, including web and
application development.

Role Description

This is a full-time, unpaid internship based in Bengaluru with a hybrid
work arrangement. The Full Stack Web Developer Intern assists with developing,
testing and maintaining web applications across frontend and backend
components. The role involves PHP server-side development, user-interface
implementation, database interactions and API integration.

Responsibilities

- Develop and maintain web applications using PHP.
- Assist with frontend and backend development.
- Build responsive interfaces using HTML, CSS and JavaScript.
- Implement server-side logic and work with databases.
- Integrate APIs and support application features.
- Test and debug code and help resolve software issues.
- Write clean, maintainable code and follow development standards.
- Participate in code reviews and document technical work.
- Collaborate with senior developers and project team members.
- Use version control tools and collaborative development practices.

Qualifications

- Foundational knowledge of programming and software development.
- Understanding of PHP or similar backend technologies.
- Basic knowledge of databases and server-side logic.
- Familiarity with HTML, CSS and JavaScript.
- React or Laravel knowledge is beneficial.
- Understanding of object-oriented programming.
- Familiarity with Git.
- Pursuing or recently completing a degree in Computer Science, IT or
  a related field is beneficial.
- Problem-solving, communication and teamwork skills.

Internship Details

Duration: 3 months.
Work arrangement: Hybrid.
Stipend: Unpaid.

Note: This is a prepared summary based on the job posting, not its
word-for-word original description.
"""
    },
    {
        "company": "Netlyft Technologies Pvt Ltd.",
        "job_title": "React Developer Intern",
        "description": """
Company and Role Summary

This React Developer Intern role is listed with Netlyft Technologies
Pvt. Ltd. in Kochi, Kerala. The listing describes a three-month, full-time,
on-site internship focused on frontend development using React.

Responsibilities

- Develop and maintain web interfaces using React.js.
- Create responsive, user-friendly interfaces.
- Build reusable UI components using JavaScript, HTML and CSS.
- Integrate APIs and manage data displayed by the application.
- Identify and fix bugs and help improve application performance.
- Collaborate with other team members on frontend development tasks.

Qualifications and Skills

- Knowledge of React.js, JavaScript, HTML and CSS.
- Understanding of responsive web design.
- Familiarity with API integration is useful.
- A React or web-development course/certification is mentioned as relevant
  preparation in the listing.
- Problem-solving skills, initiative and willingness to learn.

Internship Details

Duration: 3 months.
Work arrangement: On-site.
Location: Infopark Phase 1, Kakkanad, Kochi.

Note: This is a prepared summary based on the job posting, not its
word-for-word original description.
"""
    }
]


def main():
    if not DB_PATH.exists():
        print("ERROR: Database file not found:", DB_PATH)
        return

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Confirm the expected columns exist
    cursor.execute("PRAGMA table_info(jobs)")
    columns = {row[1] for row in cursor.fetchall()}

    if not {"job_title", "company", "description"}.issubset(columns):
        print("ERROR: Required columns are missing from the jobs table.")
        connection.close()
        return

    updated = 0
    not_found = []
    already_filled = []

    for item in descriptions:
        cursor.execute(
            """
            SELECT id, description
            FROM jobs
            WHERE job_title = ? AND company = ?
            """,
            (item["job_title"], item["company"])
        )
        row = cursor.fetchone()

        if row is None:
            not_found.append(
                f'{item["job_title"]} — {item["company"]}'
            )
            continue

        job_id, current_description = row

        if current_description and current_description.strip():
            already_filled.append(
                f'{item["job_title"]} — {item["company"]}'
            )
            continue

        cursor.execute(
            """
            UPDATE jobs
            SET description = ?
            WHERE id = ?
              AND (description IS NULL OR TRIM(description) = '')
            """,
            (item["description"].strip(), job_id)
        )

        if cursor.rowcount == 1:
            updated += 1

    connection.commit()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE description IS NOT NULL
          AND TRIM(description) != ''
    """)
    jobs_with_descriptions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE description IS NULL
           OR TRIM(description) = ''
    """)
    jobs_missing_descriptions = cursor.fetchone()[0]

    connection.close()

    print("\n--- DESCRIPTION UPDATE RESULTS ---")
    print("Descriptions added:", updated)
    print("Already had descriptions:", len(already_filled))
    print("Jobs not matched:", len(not_found))
    print("Total jobs:", total_jobs)
    print("Jobs with descriptions:", jobs_with_descriptions)
    print("Jobs still missing descriptions:", jobs_missing_descriptions)

    if already_filled:
        print("\nAlready filled (not overwritten):")
        for job in already_filled:
            print("-", job)

    if not_found:
        print("\nCould not match these jobs:")
        for job in not_found:
            print("-", job)

    if jobs_missing_descriptions:
        print("\nRun your missing-description checker to identify remaining jobs.")
    else:
        print("\nSUCCESS: Every job currently has a description.")


if __name__ == "__main__":
    main()
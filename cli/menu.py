from services.student_service import add_student, view_students, search_student, update_student, delete_student
from logs.logger import logger


def menu():

    while True:

        try:

            print("\n" + "="*40)
            print("     STUDENT MANAGEMENT SYSTEM")
            print("="*40)

            print("1️⃣  Add Student")
            print("2️⃣  View Students")
            print("3️⃣  Search Student")
            print("4️⃣  Update Student")
            print("5️⃣  Delete Student")
            print("6️⃣  Exit")

            print("-"*40)

            choice = input("Enter your choice: ").strip()

            if choice == "1":

                print("\nAdd New Student\n")

                reg_no = input("Registration Number: ").strip()
                roll_no = input("Roll Number: ").strip()
                name = input("Student Name: ").strip()

                try:
                    age = int(input("Age: "))
                except ValueError:
                    print("Age must be a number")
                    continue

                branch = input("Branch: ").strip()

                add_student(reg_no, roll_no, name, age, branch)

            elif choice == "2":
                view_students()

            elif choice == "3":

                reg_no = input("Enter registration number: ").strip()

                if not reg_no:
                    print("Registration number cannot be empty")
                    continue

                search_student(reg_no)

            elif choice == "4":

                reg_no = input("Registration number to update: ").strip()
                name = input("New name: ").strip()

                try:
                    age = int(input("New age: "))
                except ValueError:
                    print("Age must be a number")
                    continue

                branch = input("New branch: ").strip()

                update_student(reg_no, name, age, branch)

            elif choice == "5":

                reg_no = input("Registration number to delete: ").strip()

                delete_student(reg_no)

            elif choice == "6":

                print("\nExiting program...")
                logger.info("Program exited by user")
                break

            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
            logger.warning("Program interrupted by user")
            break

        except Exception as e:
            print("Unexpected error occurred")
            logger.error(f"Menu error: {e}")
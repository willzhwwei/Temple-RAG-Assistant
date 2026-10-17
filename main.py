"""Start the Temple RAG assistant after test credential verification."""

from getpass import getpass

from student_data.student_store import authenticate_student


def main():
    while True:
        student_id = input(
            "Enter your student ID (or 'exit' to quit): "
        ).strip().upper()

        if student_id == "EXIT":
            return

        if not student_id:
            print("Please enter a student ID.")
            continue

        password = getpass("Enter your password: ")

        try:
            authenticated = authenticate_student(
                student_id,
                password,
            )
        except (OSError, ValueError) as error:
            print(f"Could not read student data: {error}")
            return

        if not authenticated:
            print("Invalid student ID or password.")
            continue

        print(f"Login successful. Welcome, {student_id}!")

        from src.rag import interactive_rag

        interactive_rag(student_id=student_id)
        return


if __name__ == "__main__":
    main()
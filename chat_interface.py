import requests
import json

def get_student_details(roll_number):
    # Replace with the URL where your PHP script is hosted
    url = f"http://localhost/search_student.php?roll_number={roll_number}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            return data['data']
        else:
            return {'error': data['message']}
    else:
        return {'error': 'Failed to connect to the server'}

def chat_interface():
    print("Welcome to the Student Info Chatbot!")
    while True:
        roll_number = input("Enter the roll number to search (or 'exit' to quit): ")
        if roll_number.lower() == 'exit':
            break

        try:
            roll_number = int(roll_number)
            student_details = get_student_details(roll_number)
            if 'error' in student_details:
                print(f"Error: {student_details['error']}")
            else:
                print(f"Student Details:\nName: {student_details['name']}\nAge: {student_details['age']}\nClass: {student_details['class']}")
        except ValueError:
            print("Invalid roll number. Please enter a valid number.")

if __name__ == "__main__":
    chat_interface()

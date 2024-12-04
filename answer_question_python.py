import serial
import time
import threading
import speech_recognition as sr
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import serial.tools.list_ports

# Function to connect to Arduino
def connect_to_arduino():
    # Try to auto-detect Arduino's serial port
    ports = serial.tools.list_ports.comports()
    arduino_ports = []
    for port in ports:
        if 'Arduino' in port.description or 'Genuino' in port.description:
            arduino_ports.append(port.device)
    if not arduino_ports:
        print("Arduino not detected automatically, please enter the port manually.")
        port = input("Enter the serial port of Arduino (e.g., COM3 or /dev/ttyUSB0): ")
        try:
            arduino = serial.Serial(port, 9600)
            print(f"Connected to Arduino on port: {port}")
            return arduino
        except serial.SerialException as e:
            print(f"Failed to open serial port {port}: {e}")
            return None
    elif len(arduino_ports) == 1:
        port = arduino_ports[0]
        try:
            arduino = serial.Serial(port, 9600)
            print(f"Automatically connected to Arduino on port: {port}")
            return arduino
        except serial.SerialException as e:
            print(f"Failed to open serial port {port}: {e}")
            return None
    else:
        print("Multiple Arduino devices detected, please select one:")
        for i, port in enumerate(arduino_ports):
            print(f"{i}: {port}")
        index = int(input("Enter the index number: "))
        port = arduino_ports[index]
        try:
            arduino = serial.Serial(port, 9600)
            print(f"Connected to Arduino on port: {port}")
            return arduino
        except serial.SerialException as e:
            print(f"Failed to open serial port {port}: {e}")
            return None


# List of questions
questions = [
    "Question 1: What is the Earth's satellite?",
    "Question 2: What is the chemical formula of water?",
    "Question 3: Which is the largest planet in the solar system?"
]

# List to store user answers
user_answers = []

# List to store indices of users who have answered
user_indices = []

# Maximum number of users
user_count = 4

# Load the multilingual model
model = SentenceTransformer('distiluse-base-multilingual-cased')

# Global variables
current_user = None
current_question = ""
plagiarists = []

def read_from_arduino(ser):
    global current_user, current_question
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode().strip()
            if data.startswith("BUZZER:"):
                user_index = int(data.split(":")[1])
                if current_user is None:
                    current_user = user_index
                    handle_buzzer(user_index, ser, current_question)
                else:
                    # Another user is already responding, ignore other buzzer signals
                    pass

def handle_buzzer(user_index, ser, question):
    # Check if the user has already answered
    if user_index in user_indices:
        return
    user_indices.append(user_index)
    # Process the user's answer
    record_answer(user_index, ser, question)
    # Notify Arduino to unlock the buzzer
    command = f"UNLOCK\n"
    ser.write(command.encode())

def record_answer(user_index, ser, question):
    global current_user, plagiarists
    # Instruct Arduino to turn on the corresponding user's LED
    command = f"LED_ON:{user_index}\n"
    ser.write(command.encode())
    # Start recording
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    print(f"User {user_index} starts answering, please respond within the time limit.")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=10)  # Time limit of 10 seconds
        except sr.WaitTimeoutError:
            print(f"User {user_index} did not respond within the time limit.")
            audio = None
    # After finishing, instruct Arduino to turn off the LED
    command = f"LED_OFF:{user_index}\n"
    ser.write(command.encode())
    # Convert speech to text
    if audio:
        try:
            text = recognizer.recognize_google(audio, language='en-US')  # Change 'en-US' if needed
        except sr.UnknownValueError:
            text = ""
    else:
        text = ""
    print(f"User {user_index}'s answer: {text}")
    
    # Check if the user did not answer the question
    if not audio or text.strip() == "":
        print(f"User {user_index} did not answer the question and is considered cheating.")
        # Mark the user as a cheater
        if user_index not in plagiarists:
            plagiarists.append(user_index)
    else:
        # Check the relevance of the answer to the question
        question_embedding = model.encode(question)
        answer_embedding = model.encode(text)
        similarity = cosine_similarity([question_embedding], [answer_embedding])[0][0]
        relevant = similarity > 0.5

        if not relevant:
            print(f"User {user_index}'s answer is not relevant to the question and is considered cheating.")
            if user_index not in plagiarists:
                plagiarists.append(user_index)
        else:
            user_answers.append((user_index, text))

    # Reset current user
    current_user = None

def compare_answers():
    embeddings = []
    indices = []

    # Generate embeddings for each answer
    for index, answer in user_answers:
        if answer.strip() == "":
            embeddings.append(None)
        else:
            embedding = model.encode(answer)
            embeddings.append(embedding)
        indices.append(index)

    # Compare the similarity of answers
    for i in range(len(indices)):
        for j in range(i+1, len(indices)):
            if embeddings[i] is None or embeddings[j] is None:
                continue  # Skip empty answers
            similarity = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
            if similarity > 0.8:  # Set threshold to 0.8
                plagiarist = indices[j]
                if plagiarist not in plagiarists:
                    plagiarists.append(plagiarist)

def main():
    ser = connect_to_arduino()
    if not ser:
        print("Failed to connect to Arduino, program exits.")
        return

    global current_question, plagiarists

    # Create and start thread
    arduino_thread = threading.Thread(target=read_from_arduino, args=(ser,))
    arduino_thread.daemon = True
    arduino_thread.start()

    for question in questions:
        print(f"\nPlease listen to the question: {question}")
        time.sleep(5)  # Wait for 5 seconds

        # Set current question
        current_question = question

        # Clear previous answers and cheaters list
        user_answers.clear()
        user_indices.clear()
        plagiarists.clear()

        # Number of users allowed to answer
        allowed_users = user_count  # Adjust if needed

        while len(user_indices) < allowed_users:
            print("Start buzzing, press the button to buzz.")
            # Wait for user to buzz
            while current_user is None:
                pass  # Wait for user to buzz
            # After the user finishes answering, the loop automatically continues

        # All users have finished answering, perform plagiarism detection
        compare_answers()  # Now plagiarists list is updated
        for plagiarist in plagiarists:
            # Notify Arduino to rotate the servo
            command = f"ROTATE:{plagiarist}\n"
            ser.write(command.encode())
            print(f"User {plagiarist} is judged as cheating, servo rotates 60 degrees.")
        time.sleep(5)  # Wait for 5 seconds, prepare for the next question

    print("All questions have been completed.")
    ser.close()

if __name__ == "__main__":
    main()





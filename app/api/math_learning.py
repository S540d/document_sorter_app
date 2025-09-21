"""
Math Learning API Blueprint
Handles the multiplication table learning game for kids
"""

import random
from flask import Blueprint, request, jsonify, render_template

# Create blueprint
math_bp = Blueprint('math_learning', __name__, url_prefix='/math')


@math_bp.route('/')
def math_home():
    """Main math learning page"""
    return render_template('math_learning.html')


@math_bp.route('/api/generate-question')
def generate_question():
    """Generate a random multiplication question"""
    # Focus on tables 1-10 for the small multiplication table
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)

    return jsonify({
        'question': f"{num1} × {num2}",
        'num1': num1,
        'num2': num2,
        'correct_answer': num1 * num2
    })


@math_bp.route('/api/check-answer', methods=['POST'])
def check_answer():
    """Check if the provided answer is correct"""
    data = request.get_json()

    user_answer = data.get('answer')
    correct_answer = data.get('correct_answer')

    if user_answer is None or correct_answer is None:
        return jsonify({'error': 'Missing answer or correct_answer'}), 400

    is_correct = int(user_answer) == int(correct_answer)

    # Generate encouraging messages
    if is_correct:
        messages = [
            "Super! Das ist richtig! 🌟",
            "Fantastisch! Du bist ein Mathe-Star! ⭐",
            "Perfekt! Weiter so! 🎉",
            "Toll gemacht! Das war richtig! 👏",
            "Bravo! Du kannst das! 🚀"
        ]
    else:
        messages = [
            f"Fast richtig! Die Antwort ist {correct_answer}. Versuch's nochmal! 💪",
            f"Nicht ganz, aber du schaffst das! Die richtige Antwort ist {correct_answer}. 🌈",
            f"Ups! Die richtige Antwort ist {correct_answer}. Beim nächsten Mal klappt's! 🍀",
            f"Weiter üben! Die Antwort ist {correct_answer}. Du wirst immer besser! 📚"
        ]

    return jsonify({
        'is_correct': is_correct,
        'message': random.choice(messages),
        'correct_answer': correct_answer
    })


@math_bp.route('/api/multiplication-table/<int:number>')
def get_multiplication_table(number):
    """Get the complete multiplication table for a specific number"""
    if number < 1 or number > 10:
        return jsonify({'error': 'Number must be between 1 and 10'}), 400

    table = []
    for i in range(1, 11):
        table.append({
            'equation': f"{number} × {i} = {number * i}",
            'num1': number,
            'num2': i,
            'result': number * i
        })

    return jsonify({
        'number': number,
        'table': table
    })


@math_bp.route('/api/practice-table/<int:number>')
def practice_table(number):
    """Generate practice questions for a specific multiplication table"""
    if number < 1 or number > 10:
        return jsonify({'error': 'Number must be between 1 and 10'}), 400

    # Generate 5 random questions for this table
    questions = []
    for _ in range(5):
        multiplier = random.randint(1, 10)
        questions.append({
            'question': f"{number} × {multiplier}",
            'num1': number,
            'num2': multiplier,
            'correct_answer': number * multiplier
        })

    return jsonify({
        'table_number': number,
        'questions': questions
    })
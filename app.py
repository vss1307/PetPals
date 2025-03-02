from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson import ObjectId
import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Access the API key
api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['petpals_dashboard']
users = db['users']
pets = db['pets']

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# Configure Gemini AI
Gemini_client = genai.Client(api_key=api_key)

# Pet types and their breeds
PET_BREEDS = {
    "dog": ["Labrador", "Golden Retriever", "German Shepherd", "Bulldog", "Poodle", "Beagle", "Chihuahua", "Husky", "Dachshund", "Mixed Breed"],
    "cat": ["Persian", "Maine Coon", "Siamese", "Bengal", "Ragdoll", "Scottish Fold", "Sphynx", "Abyssinian", "British Shorthair", "Mixed Breed"],
    "bird": ["Parakeet", "Cockatiel", "Canary", "Lovebird", "Parrot", "Finch", "Macaw", "Conure", "Cockatoo", "Other"],
    "fish": ["Goldfish", "Betta", "Guppy", "Angelfish", "Tetra", "Cichlid", "Molly", "Discus", "Koi", "Other"],
    "rabbit": ["Holland Lop", "Mini Rex", "Dutch", "Netherland Dwarf", "Lionhead", "English Angora", "Flemish Giant", "Rex", "Mini Lop", "Mixed Breed"],
    "hamster": ["Syrian", "Dwarf Campbell", "Winter White", "Roborovski", "Chinese", "Other"]
}

# Helper function to check if user is logged in
def get_current_user():
    if 'user_id' in session:
        return users.find_one({"_id": ObjectId(session['user_id'])})
    return None

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/get_breeds/<pet_type>')
def get_breeds(pet_type):
    if pet_type in PET_BREEDS:
        return jsonify(PET_BREEDS[pet_type])
    return jsonify([])

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get user's pets
    user_pets = list(pets.find({"user_id": ObjectId(session['user_id'])}))
    
    # Sort events by date if they exist
    if 'events' in user:
        user['events'].sort(key=lambda x: x['date'])
    
    return render_template('dashboard.html', user=user, pets=user_pets)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        existing_user = users.find_one({'email': request.form.get('email')})
        
        if existing_user is None:
            # Hash the password
            hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
            
            # Create new user
            user_id = users.insert_one({
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'password': hashed_password,
                'avatar_url': "https://i.pravatar.cc/150?img=32",
                'member_since': datetime.now().strftime("%B %d, %Y"),
                'bio': "Pet enthusiast and proud pet owner.",
                'events': [],
                'created_at': datetime.now()
            }).inserted_id
            
            # Add pet data if available
            if 'pet_data' in session:
                pet_data = session.pop('pet_data')
                pet_data['user_id'] = user_id
                pet_data['owner'] = request.form.get('name')
                pets.insert_one(pet_data)
            
            # Log the user in
            session['user_id'] = str(user_id)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Email already exists!', 'danger')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users.find_one({'email': request.form.get('email')})
        
        if user and bcrypt.check_password_hash(user['password'], request.form.get('password')):
            session['user_id'] = str(user['_id'])
            
            # Add pet data if available
            if 'pet_data' in session:
                pet_data = session.pop('pet_data')
                pet_data['user_id'] = user['_id']
                pet_data['owner'] = user['name']
                pets.insert_one(pet_data)
                
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/pet_info', methods=['GET', 'POST'])
def pet_info():
    if request.method == 'POST':
        pet_data = {
            'type': request.form.get('pet_type'),
            'name': request.form.get('pet_name'),
            'breed': request.form.get('pet_breed'),
            'age': int(request.form.get('pet_age')),
            'weight': request.form.get('pet_weight'),
            'vaccinated': request.form.get('vaccinated') == 'on',
            'feeding_schedule': "Morning and evening",
            'vaccination_date': datetime.now().strftime("%Y-%m-%d"),
            'grooming_schedule': "Weekly",
            'walking_schedule': "Morning and evening" if request.form.get('pet_type') == "dog" else "N/A",
            'treat_time': "After walks or training",
            'created_at': datetime.now()
        }
        
        # Set default image based on pet type
        pet_type = pet_data['type'].lower()
        if pet_type == 'dog':
            pet_data['image_url'] = "https://images.unsplash.com/photo-1552053831-71594a27632d?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        elif pet_type == 'cat':
            pet_data['image_url'] = "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        elif pet_type == 'bird':
            pet_data['image_url'] = "https://images.unsplash.com/photo-1552728089-57bdde30beb3?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YmlyZHxlbnwwfHwwfHx8MA%3D%3D"
        elif pet_type == 'fish':
            pet_data['image_url'] = "https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8ZmlzaHxlbnwwfHwwfHx8MA%3D%3D"
        else:
            pet_data['image_url'] = "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        
        # If user is logged in, add pet directly
        if 'user_id' in session:
            user = users.find_one({"_id": ObjectId(session['user_id'])})
            pet_data['user_id'] = ObjectId(session['user_id'])
            pet_data['owner'] = user['name']
            pets.insert_one(pet_data)
            return redirect(url_for('dashboard'))
        else:
            # Store pet data in session for later use after user signup/login
            session['pet_data'] = pet_data
            return redirect(url_for('signup'))
        
    return render_template('pet_info.html', pet_breeds=PET_BREEDS)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        updated_user = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'bio': request.form.get('bio')
        }
        
        # Keep existing fields
        for key in user:
            if key not in updated_user and key != '_id':
                updated_user[key] = user[key]
        
        # Handle profile image upload
        if 'profile_image' in request.files and request.files['profile_image'].filename:
            profile_image = request.files['profile_image']
            
            # Generate a secure filename
            filename = secure_filename(profile_image.filename)
            
            # Create a unique filename with timestamp
            file_ext = os.path.splitext(filename)[1]
            unique_filename = f"profile_{uuid.uuid4().hex}{file_ext}"
            
            # Ensure upload directory exists
            upload_dir = os.path.join(app.static_folder, 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(upload_dir, unique_filename)
            profile_image.save(file_path)
            
            # Set the avatar URL in the database
            updated_user['avatar_url'] = f"/static/uploads/profiles/{unique_filename}"
            
            # Delete the old image file if it exists and isn't a default image
            if 'avatar_url' in user and not user['avatar_url'].startswith('https://'):
                try:
                    old_image_path = os.path.join(app.root_path, 'static', user['avatar_url'].replace('/static/', ''))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except Exception as e:
                    print(f"Error removing old profile image: {e}")
        
        # Update user
        users.update_one({"_id": user["_id"]}, {"$set": updated_user})
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_profile.html', user=user)

@app.route('/add_event', methods=['POST'])
def add_event():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get form data
    new_event = {
        'title': request.form.get('title'),
        'date': request.form.get('date'),
        'description': request.form.get('description'),
        'icon': request.form.get('icon')
    }
    
    # Add pet reference if provided
    pet_id = request.form.get('pet_id')
    if pet_id:
        new_event['pet_id'] = pet_id
        # Get pet name for the event title if not already specified
        pet = pets.find_one({'_id': ObjectId(pet_id)})
        if pet:
            new_event['pet_name'] = pet['name']
    
    # Add event to user's events array
    users.update_one(
        {"_id": user["_id"]},
        {"$push": {"events": new_event}}
    )
    
    flash('Event added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/get_event/<event_index>')
def get_event(event_index):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    try:
        event_index = int(event_index)
        if 'events' in user and event_index < len(user['events']):
            return jsonify({
                'success': True,
                'event': user['events'][event_index]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Event not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/update_event', methods=['POST'])
def update_event():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    event_index = int(request.form.get('event_index'))
    
    # Get form data
    updated_event = {
        'title': request.form.get('title'),
        'date': request.form.get('date'),
        'description': request.form.get('description'),
        'icon': request.form.get('icon')
    }
    
    # Add pet reference if provided
    pet_id = request.form.get('pet_id')
    if pet_id:
        updated_event['pet_id'] = pet_id
        # Get pet name for the event title if not already specified
        pet = pets.find_one({'_id': ObjectId(pet_id)})
        if pet:
            updated_event['pet_name'] = pet['name']
    
    # Update the event in the user's events array
    if 'events' in user and event_index < len(user['events']):
        user['events'][event_index] = updated_event
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"events": user['events']}}
        )
    
    flash('Event updated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_event/<event_index>', methods=['POST'])
def delete_event(event_index):
    user = get_current_user()
    if not user:
        return 'User not logged in', 401
    
    try:
        event_index = int(event_index)
        
        if 'events' in user and event_index < len(user['events']):
            # Remove the event at the specified index
            user['events'].pop(event_index)
            
            # Update the user document
            users.update_one(
                {"_id": user["_id"]},
                {"$set": {"events": user['events']}}
            )
            
            return '', 204  # No content, success
        else:
            return 'Event not found', 404
    except Exception as e:
        return str(e), 500

@app.route('/pet/<pet_id>')
def pet_details(pet_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    pet = pets.find_one({'_id': ObjectId(pet_id)})
    if not pet or str(pet.get('user_id')) != session['user_id']:
        flash('Pet not found or you do not have permission to view this pet', 'danger')
        return redirect(url_for('dashboard'))
    
    # Basic pet info for prompts
    pet_info = f"Pet: {pet['name']}, Type: {pet['type']}, Breed: {pet['breed']}, Age: {pet['age']}"
    
    # Get fun facts specific to the pet
    fun_facts_prompt = f"Give 3-5 interesting and fun facts about {pet['breed']} {pet['type']}s. Format as a bulleted list."
    try:
        fun_facts_response = Gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=fun_facts_prompt)
        fun_facts = fun_facts_response.text
    except Exception as e:
        print(f"Error getting fun facts: {e}")
        fun_facts = "Could not generate fun facts at this time."
    
    # Get care recommendations for the pet
    care_prompt = f"Give specific care recommendations for a {pet['breed']} {pet['type']} that is {pet['age']} years old. Include advice on diet, exercise, grooming, and health concerns. Format as a bulleted list with category headers. Each point should be short and concise. Give 3 to 5 points"
    try:
        care_response = Gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=care_prompt)
        care_recommendations = care_response.text
    except Exception as e:
        print(f"Error getting care recommendations: {e}")
        care_recommendations = "Could not generate care recommendations at this time."
    
    return render_template('pet_details.html', 
                          pet=pet, 
                          fun_facts=fun_facts, 
                          care_recommendations=care_recommendations)

@app.route('/add_pet', methods=['GET', 'POST'])
def add_pet():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Initialize pet data from form
        new_pet = {
            'name': request.form.get('name'),
            'type': request.form.get('type'),
            'breed': request.form.get('breed'),
            'age': int(request.form.get('age')),
            'user_id': ObjectId(session['user_id']),
            'owner': user['name'],
            'feeding_schedule': request.form.get('feeding_schedule'),
            'vaccination_date': request.form.get('vaccination_date'),
            'grooming_schedule': request.form.get('grooming_schedule'),
            'walking_schedule': request.form.get('walking_schedule'),
            'treat_time': request.form.get('treat_time'),
            'created_at': datetime.now()
        }
        
        # Handle pet image upload
        if 'pet_image' in request.files and request.files['pet_image'].filename:
            pet_image = request.files['pet_image']
            
            # Generate a secure filename
            filename = secure_filename(pet_image.filename)
            
            # Create a unique filename with timestamp
            file_ext = os.path.splitext(filename)[1]
            unique_filename = f"pet_{uuid.uuid4().hex}{file_ext}"
            
            # Ensure upload directory exists
            upload_dir = os.path.join(app.static_folder, 'uploads', 'pets')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(upload_dir, unique_filename)
            pet_image.save(file_path)
            
            # Set the image URL in the database
            new_pet['image_url'] = f"/static/uploads/pets/{unique_filename}"
        else:
            # Set default image based on pet type
            pet_type = new_pet['type'].lower()
            if pet_type == 'dog':
                new_pet['image_url'] = "https://images.unsplash.com/photo-1552053831-71594a27632d?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
            elif pet_type == 'cat':
                new_pet['image_url'] = "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
            elif pet_type == 'bird':
                new_pet['image_url'] = "https://images.unsplash.com/photo-1552728089-57bdde30beb3?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YmlyZHxlbnwwfHwwfHx8MA%3D%3D"
            elif pet_type == 'fish':
                new_pet['image_url'] = "https://images.unsplash.com/photo-1522069169874-c58ec4b76be5?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8ZmlzaHxlbnwwfHwwfHx8MA%3D%3D"
            elif pet_type == 'reptile':
                new_pet['image_url'] = "https://images.unsplash.com/photo-1610629651605-0b181ad69aab?q=80&w=1974&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
            else:
                new_pet['image_url'] = "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        
        # Insert the new pet
        pets.insert_one(new_pet)
        
        flash('Pet added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_pet.html', pet_breeds=PET_BREEDS)

@app.route('/edit_pet/<pet_id>', methods=['GET', 'POST'])
def edit_pet(pet_id):
    user = get_current_user()
    if not user:
     return redirect(url_for('login'))


    pet = pets.find_one({'_id': ObjectId(pet_id)})
    if not pet or str(pet.get('user_id')) != session['user_id']:
        flash('Pet not found or you do not have permission to edit this pet', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Initialize updated pet data from form
        updated_pet = {
            'name': request.form.get('name'),
            'type': request.form.get('type'),
            'breed': request.form.get('breed'),
            'age': int(request.form.get('age')),
            'feeding_schedule': request.form.get('feeding_schedule'),
            'vaccination_date': request.form.get('vaccination_date'),
            'grooming_schedule': request.form.get('grooming_schedule'),
            'walking_schedule': request.form.get('walking_schedule'),
            'treat_time': request.form.get('treat_time')
        }
        
        # Handle pet image upload
        if 'pet_image' in request.files and request.files['pet_image'].filename:
            pet_image = request.files['pet_image']
            
            # Generate a secure filename
            filename = secure_filename(pet_image.filename)
            
            # Create a unique filename with timestamp
            file_ext = os.path.splitext(filename)
            unique_filename = f"pet_{uuid.uuid4().hex}{file_ext}"
            
            # Ensure upload directory exists
            upload_dir = os.path.join(app.static_folder, 'uploads', 'pets')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(upload_dir, unique_filename)
            pet_image.save(file_path)
            
            # Set the image URL in the database
            updated_pet['image_url'] = f"/static/uploads/pets/{unique_filename}"
            
            # Delete the old image file if it exists and isn't a default image
            if 'image_url' in pet and not pet['image_url'].startswith('https://'):
                try:
                    old_image_path = os.path.join(app.root_path, 'static', pet['image_url'].replace('/static/', ''))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except Exception as e:
                    print(f"Error removing old pet image: {e}")
        
        # Update the pet
        pets.update_one({"_id": ObjectId(pet_id)}, {"$set": updated_pet})
        
        flash('Pet updated successfully!', 'success')
        return redirect(url_for('pet_details', pet_id=pet_id))

    return render_template('edit_pet.html', pet=pet, pet_breeds=PET_BREEDS) 

@app.route('/delete_pet', methods=['POST'])
def delete_pet():
    pet_id = request.form.get('pet_id')
    
    # Get the pet to delete (to access the image path)
    pet = pets.find_one({'_id': ObjectId(pet_id)})
    
    if pet:
        # Delete the pet's image if it's not a default image
        if pet['image_url'] and not pet['image_url'].startswith('/static/images/default_'):
            try:
                image_path = os.path.join(app.root_path, 'static', pet['image_url'].replace('/static/', ''))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                # Log the error but continue with the deletion
                print(f"Error removing pet image: {e}")
        
        # Delete the pet from the database
        pets.delete_one({'_id': ObjectId(pet_id)})
    
    return redirect(url_for('dashboard'))



@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/community')
def community():
    return render_template('community.html')

@app.route('/ai_help', methods=['GET', 'POST'])
def ai_help():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    response = None
    
    if request.method == 'POST':
        question = request.form.get('question')
        response = Gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=f"As a pet care expert, answer this question: {question}")
    
    return render_template('ai_help.html', response=response.text if response else None)

@app.route('/generate_schedule', methods=['POST'])
def generate_schedule():
    user = get_current_user()
    if not user:
        if not user:
           return redirect(url_for('login'))
        
    data = request.json
    
    # Format the prompt for Gemini
    pets_info = ""
    for pet in data['pets']:
        pets_info += f"Pet: {pet['name']} ({pet['type']}, {pet['breed']}, {pet['age']} years old)\n"
        pets_info += f"- Feeding: {pet['feeding_schedule']}\n"
        if pet['walking_schedule'] and pet['walking_schedule'] != 'N/A':
            pets_info += f"- Walking: {pet['walking_schedule']}\n"
        pets_info += f"- Grooming: {pet['grooming_schedule']}\n"
        pets_info += f"- Treats: {pet['treat_time']}\n\n"
    
    prompt = f"""Create a detailed daily schedule for a pet owner on {data['date']} from {data['wakeTime']} to {data['sleepTime']}.
    
Pet information:
{pets_info}

Owner's schedule:
- At home: {data['homeTimes']}
- Outside (work/errands): {data['outsideTimes']}
- Additional activities planned: {data['activities'] if data['activities'] else 'None'}

Please create an hour-by-hour schedule that includes all pet care tasks (feeding, walking, grooming, etc.) integrated with the owner's daily routine. Make sure pet care activities happen when the owner is at home.

IMPORTANT: Format your response in the following structure:
1. Start with a line "==SUMMARY==" followed by a brief summary of the day
2. Then a line "==SCHEDULE==" followed by the hour-by-hour schedule
3. Each schedule item should be in the format "TIME - ACTIVITY"
4. End with a line "==TIPS==" followed by 2-3 pet care tips specific to this schedule

Example format:
==SUMMARY==
Brief summary here...

==SCHEDULE==
6:00 AM - Wake up and morning routine
6:30 AM - Feed Rex and Whiskers
...

==TIPS==
1. Tip one here
2. Tip two here
...
"""

    
    # Call Gemini API
    try:
        response = Gemini_client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt)
        schedule = response.text
        current_time = datetime.now()
        schedule_data = {
            'date': data['date'],
            'wakeTime': data['wakeTime'],
            'sleepTime': data['sleepTime'],
            'homeTimes': data['homeTimes'],
            'outsideTimes': data['outsideTimes'],
            'activities': data['activities'],
            'schedule': schedule,
            'generated_at': current_time.isoformat()
        }
        
        # Update user document with the new schedule
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_schedule": schedule_data}}
        )
        return jsonify({"raw_schedule": schedule})
    except Exception as e:
        print(f"Error in generate_schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "raw_schedule": f"Error: {str(e)}"})

# Market Section

products = db['products']
cart_collection = db['cart']

@app.route('/market')
def market():
    user = get_current_user()
    
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    # Build the query
    query = {}
    if category:
        query['category'] = category
    
    # Add search functionality
    if search:
        # Create a case-insensitive search across multiple fields
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}},
            {'category': {'$regex': search, '$options': 'i'}}
        ]

    # Sort the products
    if sort == 'price':
        sort_key = 'price'
    else:
        sort_key = 'name'

    sort_direction = 1 if order == 'asc' else -1

    items = list(products.find(query).sort(sort_key, sort_direction))
    categories = products.distinct('category')

    return render_template('market.html', items=items, categories=categories, user=user)


# Modify the cart collection structure to include user_id
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Please log in to add items to cart'})
    
    item_id = request.form.get('item_id')
    
    # Get the product details
    product = products.find_one({'_id': ObjectId(item_id)})
    
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})
    
    # Check if the item is already in the user's cart
    cart_item = cart_collection.find_one({
        'user_id': ObjectId(user['_id']),
        'product_id': item_id
    })
    
    if cart_item:
        # Update quantity if already in cart
        cart_collection.update_one(
            {'_id': cart_item['_id']},
            {'$inc': {'quantity': 1}}
        )
    else:
        # Add new item to cart with user_id
        cart_collection.insert_one({
            'user_id': ObjectId(user['_id']),
            'product_id': item_id,
            'name': product['name'],
            'price': product['price'],
            'image_url': product.get('image_url', ''),
            'description': product.get('description', ''),
            'quantity': 1,
            'added_at': datetime.now()
        })
    
    return jsonify({'success': True, 'message': 'Item added to cart'})

@app.route('/cart')
def cart():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Fetch cart items for the current user
    cart_items = list(cart_collection.find({'user_id': ObjectId(user['_id'])}))
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return render_template('cart.html', items=cart_items, total=total)



@app.route('/update_cart', methods=['POST'])
def update_cart():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    item_id = request.form.get('item_id')
    action = request.form.get('action')
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        # Verify the cart item belongs to the current user
        cart_item = cart_collection.find_one({
            '_id': ObjectId(item_id),
            'user_id': ObjectId(user['_id'])
        })
        
        if not cart_item:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Item not found in your cart'})
            return redirect(url_for('cart'))
        
        item = None
        item_quantity = 0
        item_total = 0
        
        if action == 'increase':
            # Increase quantity
            cart_collection.update_one(
                {'_id': ObjectId(item_id)},
                {'$inc': {'quantity': 1}}
            )
            
            # Get updated item
            item = cart_collection.find_one({'_id': ObjectId(item_id)})
            if item:
                item_quantity = item['quantity']
                item_total = item['price'] * item['quantity']
            
        elif action == 'decrease':
            # Get current quantity
            if cart_item['quantity'] > 1:
                # Decrease quantity
                cart_collection.update_one(
                    {'_id': ObjectId(item_id)},
                    {'$inc': {'quantity': -1}}
                )
                # Get updated item
                item = cart_collection.find_one({'_id': ObjectId(item_id)})
                if item:
                    item_quantity = item['quantity']
                    item_total = item['price'] * item['quantity']
            else:
                # Remove item if quantity would be 0
                cart_collection.delete_one({'_id': ObjectId(item_id)})
                item_quantity = 0
                item_total = 0
                
        elif action == 'remove':
            # Remove item completely
            cart_collection.delete_one({'_id': ObjectId(item_id)})
            item_quantity = 0
            item_total = 0
        
        # Get updated cart information for the current user
        cart_items = list(cart_collection.find({'user_id': ObjectId(user['_id'])}))
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        total = subtotal + 5.99  # Adding shipping cost
        
        # If this is an AJAX request, return JSON
        if is_ajax:
            return jsonify({
                'success': True,
                'item_quantity': item_quantity,
                'item_total': item_total,
                'subtotal': subtotal,
                'total': total,
                'items_count': len(cart_items)
            })
        
        # Otherwise redirect back to cart page
        return redirect(url_for('cart'))
        
    except Exception as e:
        if is_ajax:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Only delete cart items belonging to the current user
    cart_collection.delete_many({'user_id': ObjectId(user['_id'])})
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Get the user's cart items
    cart_items = list(cart_collection.find({'user_id': ObjectId(user['_id'])}))
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    # Calculate total
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    shipping = 5.99
    total = subtotal + shipping
    
    # This would typically process the order and payment
    # For now, just clear the cart and show a message
    cart_collection.delete_many({'user_id': ObjectId(user['_id'])})
    
    return render_template('checkout.html', 
                          user=user, 
                          items=cart_items, 
                          subtotal=subtotal,
                          shipping=shipping,
                          total=total)

@app.route('/api/cart')
def api_cart():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    cart_items = list(cart_collection.find({'user_id': ObjectId(user['_id'])}))
    
    # Convert ObjectId to string for JSON serialization
    for item in cart_items:
        item['_id'] = str(item['_id'])
        item['user_id'] = str(item['user_id'])
    
    return jsonify({'items': cart_items})

@app.route('/api/cart/count')
def api_cart_count():
    user = get_current_user()
    if not user:
        return jsonify({'count': 0})
    
    count = cart_collection.count_documents({'user_id': ObjectId(user['_id'])})
    return jsonify({'count': count})

@app.route('/init_db')
def init_db():
    # Clear existing products
    products.delete_many({})
    
    # Sample products
    sample_products = [
        {
            "name": "Premium Dog Food",
            "price": 29.99,
            "description": "High-quality dog food for all breeds. Made with real chicken and vegetables, this premium dog food provides all the nutrients your furry friend needs for a healthy and active lifestyle.",
            "category": "dog",
            "image_url": "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Cat Toy Set",
            "price": 15.99,
            "description": "A set of interactive toys for cats. Includes feather wands, balls with bells, and catnip-filled mice that will keep your feline friend entertained for hours.",
            "category": "cat",
            "image_url": "https://images.unsplash.com/photo-1545249390-6bdfa286032f?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Fish Tank Filter",
            "price": 39.99,
            "description": "Efficient filter for aquariums up to 50 gallons. This three-stage filtration system keeps your aquarium water crystal clear and provides a healthy environment for your fish.",
            "category": "fish",
            "image_url": "https://images.unsplash.com/photo-1545249390-6bdfa286032f?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Bird Cage",
            "price": 49.99,
            "description": "Spacious cage for small to medium-sized birds. Features multiple perches, feeding stations, and a swing for your feathered friend to enjoy.",
            "category": "bird",
            "image_url": "https://images.unsplash.com/photo-1552728089-57bdde30beb3?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Hamster Wheel",
            "price": 12.99,
            "description": "Silent spinner wheel for hamsters and other small pets. The smooth-running design ensures your pet can exercise without disturbing your sleep.",
            "category": "small_pet",
            "image_url": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Dog Collar",
            "price": 9.99,
            "description": "Adjustable collar for dogs of all sizes. Made from durable nylon with a secure buckle and ID tag attachment.",
            "category": "dog",
            "image_url": "https://images.unsplash.com/photo-1545249390-6bdfa286032f?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Cat Scratching Post",
            "price": 24.99,
            "description": "Tall scratching post with a plush perch. Helps protect your furniture while giving your cat a dedicated place to scratch and relax.",
            "category": "cat",
            "image_url": "https://images.unsplash.com/photo-1545249390-6bdfa286032f?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        },
        {
            "name": "Reptile Heat Lamp",
            "price": 18.99,
            "description": "Adjustable heat lamp for reptile terrariums. Provides the warmth your cold-blooded pet needs to thrive.",
            "category": "reptile",
            "image_url": "https://images.unsplash.com/photo-1591871937573-74dbba515c4c?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=60"
        }
    ]
    
    products.insert_many(sample_products)
    return "Database initialized with sample products!"


if __name__ == '__main__':
    app.run(debug=True)

# Step 1: Use a Python base image
FROM python:3.13

# Step 2: Set environment variable for non-buffered output
ENV PYTHONUNBUFFERED=1

# Step 3: Set the working directory inside the container
WORKDIR /code

# Step 4: Copy the requirements file into the container
COPY requirements.txt .

# Step 5: Install the dependencies
RUN pip install -r requirements.txt

# Step 6: Copy the rest of your project files into the container
COPY . .

# Step 7: Expose the port Django will run on
EXPOSE 80

# Step 8: Command to run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]

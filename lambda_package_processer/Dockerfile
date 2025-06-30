# Use the official AWS Lambda Python 3.11 image
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory
WORKDIR /var/task

# Copy only requirements first (for layer caching)
COPY requirements.txt .

# Install dependencies using Python 3.11
RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install -r requirements.txt -t .

# Now copy the rest of your code
COPY . .

# Set the Lambda handler
CMD ["lambda_function.lambda_handler"]

FROM node:18

# Install LibreOffice and Python3 + pip
RUN apt-get update && \
    apt-get install -y libreoffice python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean

# Install required Python packages
COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app

# Install Node dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of your code
COPY . .

# Expose the port
EXPOSE 3000

# Run the app
CMD ["node", "server.js"]

# Use a lightweight Node.js image
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the Next.js app
COPY . .

# Build the optimized production version of the React app
RUN npm run build

# Expose the frontend port
EXPOSE 3000

# Start the Next.js production server
CMD ["npm", "start"]
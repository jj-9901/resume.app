// parser.js
const fs = require('fs');
const pdfParse = require('pdf-parse');

async function parseResume(filePath) {
  // TODO: Implement your actual parsing logic here.
  // You can use libraries like `pdf-parse`, `pdf2json`, or even NLP models.

  // convert the pdf to text
  const dataBuffer = fs.readFileSync(filePath);
  const pdfData = await pdfParse(dataBuffer);
  const text = pdfData.text;

  // Regex patterns
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  const phoneRegex = /\+?\(?\d{1,3}\)?[\s-]?\d{1,4}[\s-]?\d{3}[\s-]?\d{4}/;

  //match the patterns
  const emailMatch = text.match(emailRegex);
  const phoneMatch = text.match(phoneRegex);

  // Create a parsed data object
  const parsedData = {
    email: emailMatch ? emailMatch[0] : null,
    phone: phoneMatch ? phoneMatch[0] : null,
  };
  
  const dummyData = {
    name: "John Doe",
    email: "john.doe@example.com",
    skills: ["JavaScript", "Node.js", "React"],
    experience: "3 years"
  };

  // Optionally delete the uploaded file after parsing
  fs.unlink(filePath, (err) => {
    if (err) console.error('Failed to delete file:', err);
  });

  return parsedData;
}

module.exports = parseResume;


const fs = require('fs');
const path = require('path');
const pdfParse = require('pdf-parse');
const { execFile } = require('child_process');



// Function to print text in blocks separated by blank lines
function printTextBlocks(text) {
  console.log('\n📄 Text Blocks:\n-------------------');
  const blocks = text.split(/\n\s*\n/); // Split by two or more newlines
  blocks.forEach((block, index) => {
    const trimmed = block.trim();
    if (trimmed.length > 0) {
      console.log(`\n🔹 Block ${index + 1}:\n${trimmed}`);
    }
  });
}

function printExtractedBlocks(extractedData) {
  const blocks = {};

  extractedData.forEach(line => {
    const blockId = line.block || 0;
    if (!blocks[blockId]) blocks[blockId] = [];
    blocks[blockId].push(line.text);
  });

  console.log('\n📄 Extracted Blocks:\n-------------------');
  Object.entries(blocks).forEach(([blockId, texts]) => {
    console.log(`\n🔹 Block ${blockId}:\n${texts.join('\n')}`);
  });
}



// Run extract.py to get detailed PDF info object
const extractPdfData = (pdfFilePath) => {
  return new Promise((resolve) => {
    const extractPath = path.join(__dirname, 'extract.py');

    execFile('python', [extractPath, pdfFilePath], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ extract.py error:', error.message);
        return resolve(null);
      }

      try {
        const data = JSON.parse(stdout);
        // console.log('✅ Raw JSON from extract.py:', stdout);
        resolve(data);
      } catch (e) {
        console.error('❌ Failed to parse JSON from extract.py:', e.message);
        resolve(null);
      }
    });
  });
};

// Run name.py to extract the name from the extracted data
const getNameFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const namePath = path.join(__dirname, 'name.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [namePath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ name.py error:', error.message);
        return resolve(null);
      }

      resolve(stdout.trim());
    });
  });
};



// Add to parser.js near where you call name.py

const getSkillsFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const skillsPath = path.join(__dirname, 'skills.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [skillsPath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ skills.py error:', error.message);
        return resolve([]);
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse skills JSON:', e.message);
        resolve([]);
      }
    });
  });
};


const getExperienceFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const experiencePath = path.join(__dirname, 'experience.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [experiencePath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ experience.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse experience JSON:', e.message);
        resolve({});
      }
    });
  });
};


// Main function to parse a resume PDF
async function parseResume(filePath) {
  let finalText = '';
  let extractedData = null;

  try {
    const dataBuffer = fs.readFileSync(filePath);
    const pdfData = await pdfParse(dataBuffer);
    
    finalText = pdfData.text;

    // Run extract.py for structured fallback data
    extractedData = await extractPdfData(filePath);

    // If the extracted text is too short, use fallback
    if (!finalText || finalText.trim().length < 10) {
      if (extractedData && Array.isArray(extractedData.data)) {
        finalText = extractedData.data
          .map(item => item.text)
          .filter(line => line && line.trim().length > 0)
          .join('\n')
          .trim();

        console.log('✅ Fallback used. Final text:');
      } else {
        console.warn('⚠️ Fallback extraction failed: No valid "data" array.');
      }
    }

      console.log(finalText);
      console.log("BLOCKS");
      printExtractedBlocks(extractedData.data);
      // printTextBlocks(finalText);

  } catch (err) {
    console.error('❌ Error parsing PDF:', err.message);
    return null;
  }

  // Define regex patterns for email and phone
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  const phoneRegex = /\+?\(?\d{1,3}\)?[\s-]?\d{1,4}[\s-]?\d{3}[\s-]?\d{4}/;

  // Match email and phone
  const emailMatch = finalText.match(emailRegex);
  const phoneMatch = finalText.match(phoneRegex);

  // Get name from extracted data
  const name = extractedData ? await getNameFromExtractedData(extractedData) : null;
  const skills = extractedData ? await getSkillsFromExtractedData(extractedData) : [];
  const experience = extractedData ? await getExperienceFromExtractedData(extractedData) : [];

  // Parsed resume data
  const parsedData = {
    name: name || null,
    email: emailMatch ? emailMatch[0] : null,
    phone: phoneMatch ? phoneMatch[0] : null,
    skills: skills,
    experience: experience
  };

  // Delete file after processing
  fs.unlink(filePath, (err) => {
    if (err) console.error('⚠️ Failed to delete file:', err.message);
  });

  return parsedData;
}

module.exports = parseResume;
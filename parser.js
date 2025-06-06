
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


const getEducationFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const educationPath = path.join(__dirname, 'education.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [educationPath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ education.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse education JSON:', e.message);
        resolve({});
      }
    });
  });
};


const getProjectsFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const projectsPath = path.join(__dirname, 'projects.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [projectsPath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ projects.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse projects JSON:', e.message);
        resolve({});
      }
    });
  });
};


const getAchievementsFromExtractedData = (extractedData) => {
  return new Promise((resolve) => {
    const achievementsPath = path.join(__dirname, 'achievements.py');
    const jsonStr = JSON.stringify(extractedData);

    execFile('python', [achievementsPath, jsonStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ achievements.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse achievements JSON:', e.message);
        resolve({});
      }
    });
  });
};


// Add this function to parser.js (place it with the other similar functions)
const getExtraInfoFromExtractedData = (extractedData, usedKeys) => {
  return new Promise((resolve) => {
    const extraPath = path.join(__dirname, 'extra.py');
    const jsonStr = JSON.stringify(extractedData);
    const usedKeysStr = JSON.stringify(usedKeys);

    execFile('python', [extraPath, jsonStr, usedKeysStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ extra.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse extra info JSON:', e.message);
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
  // const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  // const phoneRegex = /\+?\(?\d{1,3}\)?[\s-]?\d{1,4}[\s-]?\d{3}[\s-]?\d{4}/;
  // Define improved regex patterns


  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
  const phoneRegex = /\b(?:\+?\d{1,3}[\s\-()]*)?(?:\(?\d{2,4}\)?[\s\-]*)?\d{3,4}[\s\-]?\d{4}\b/;

  // Filter function to avoid false phone matches
  const isLikelyValidPhoneContext = (text) => {
    const lower = text.toLowerCase();
    return !(
      lower.includes('@') ||
      lower.includes('http') ||
      lower.includes('linkedin.com') ||
      lower.includes('github.com')
    );
  };

  // Match email
  const emailMatch = finalText.match(emailRegex);

  // Match phone only if it’s not inside suspicious context
  let phoneMatch = null;
  if (isLikelyValidPhoneContext(finalText)) {
    const matchedPhone = finalText.match(phoneRegex);
    if (matchedPhone) phoneMatch = matchedPhone;
  }


  
// Update the parseResume function (replace the final part where parsedData is created)
  // Get all the parsed data
  const name = extractedData ? await getNameFromExtractedData(extractedData) : null;
  const skills = extractedData ? await getSkillsFromExtractedData(extractedData) : [];
  const experience = extractedData ? await getExperienceFromExtractedData(extractedData) : [];
  const projects = extractedData ? await getProjectsFromExtractedData(extractedData) : [];
  const education = extractedData ? await getEducationFromExtractedData(extractedData) : [];
  const achievements = extractedData ? await getAchievementsFromExtractedData(extractedData) : [];

  // Track all the keys we've already used
  const usedKeys = [
    ...(name ? ['name'] : []),
    ...(skills.length ? ['skills'] : []),
    ...(experience.length ? ['experience'] : []),
    ...(projects.length ? ['projects'] : []),
    ...(education.length ? ['education'] : []),
    ...(achievements.length ? ['achievements'] : []),
    ...(emailMatch ? ['email'] : []),
    ...(phoneMatch ? ['phone'] : [])
  ];

  // Get any remaining info not captured by other extractors
  const extraInfo = extractedData ? await getExtraInfoFromExtractedData(extractedData, usedKeys) : {};

  // Parsed resume data
  const parsedData = {
    name: name || null,
    email: emailMatch ? emailMatch[0] : null,
    phone: phoneMatch ? phoneMatch[0] : null,
    skills: skills,
    education: education,
    experience: experience,
    projects: projects,
    achievements: achievements,
    ...extraInfo  // Include any additional info
  };

  // Delete file after processing
  fs.unlink(filePath, (err) => {
    if (err) console.error('⚠️ Failed to delete file:', err.message);
  });

  return parsedData;
}

module.exports = parseResume;
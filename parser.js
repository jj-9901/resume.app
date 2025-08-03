
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
       console.log('📤 STDOUT from extract.py:', stdout);
      console.log('⚠️ STDERR from extract.py:', stderr);

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
        return resolve({ skills: [], used_block: null });
      }

      try {
        const result = JSON.parse(stdout);
        resolve({
          skills: result.skills || [],
          used_block: result.used_block ?? null
        });
      } catch (e) {
        console.error('❌ Failed to parse skills JSON:', e.message);
        resolve({ skills: [], used_block: null });
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
        return resolve({ experience: [], used_block: null });
      }

      try {
        const result = JSON.parse(stdout);
        resolve({
          experience: result.experience || [],
          used_block: result.used_block ?? null
        });
      } catch (e) {
        console.error('❌ Failed to parse experience JSON:', e.message);
        resolve({ experience: [], used_block: null });
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
        return resolve({ education: [], used_block: null });
      }

      try {
        const result = JSON.parse(stdout);
        resolve({
          education: result.education || [],
          used_block: result.used_block ?? null
        });
      } catch (e) {
        console.error('❌ Failed to parse education JSON:', e.message);
        resolve({ education: [], used_block: null });
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
        return resolve({ projects: [], used_block: null });
      }

      try {
        const result = JSON.parse(stdout);
        resolve({
          projects: result.projects || [],
          used_block: result.used_block ?? null
        });
      } catch (e) {
        console.error('❌ Failed to parse projects JSON:', e.message);
        resolve({ projects: [], used_block: null });
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
        return resolve({ achievements: [], used_block: null });
      }

      try {
        const result = JSON.parse(stdout);
        resolve({
          achievements: result.achievements || [],
          used_block: result.used_block ?? null
        });
      } catch (e) {
        console.error('❌ Failed to parse achievements JSON:', e.message);
        resolve({ achievements: [], used_block: null });
      }
    });
  });
};




const getExtraFromExtractedData = (extractedData, usedBlockSet = []) => {
  return new Promise((resolve) => {
    const extraPath = path.join(__dirname, 'extra.py');
    const jsonStr = JSON.stringify(extractedData || {});
    const usedBlocksStr = JSON.stringify([...usedBlockSet]);

    execFile('python', [extraPath, jsonStr, usedBlocksStr], (error, stdout, stderr) => {
      if (error) {
        console.error('❌ extra.py error:', error.message);
        return resolve({});
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (e) {
        console.error('❌ Failed to parse extra JSON:', e.message);
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
    
    const usedBlockSet = new Set();


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

  const usedBlockSet = new Set();


  const name = extractedData ? await getNameFromExtractedData(extractedData): null;
  const skillResult = extractedData ? await getSkillsFromExtractedData(extractedData) : { skills: [], used_block: null };
  const skills = skillResult.skills;
  if (skillResult.used_block !== null) usedBlockSet.add(skillResult.used_block);

  const educationResult = extractedData ? await getEducationFromExtractedData(extractedData) : { education: [], used_block: null };
  const education = educationResult.education;
  if (educationResult.used_block !== null) usedBlockSet.add(educationResult.used_block);

  const experienceResult = extractedData ? await getExperienceFromExtractedData(extractedData) : { experience: [], used_block: null };
  const experience = experienceResult.experience;
  if (experienceResult.used_block !== null) usedBlockSet.add(experienceResult.used_block);

  const projectsResult = extractedData ? await getProjectsFromExtractedData(extractedData) : { projects: [], used_block: null };
  const projects = projectsResult.projects;
  if (projectsResult.used_block !== null) usedBlockSet.add(projectsResult.used_block);

  const achievementsResult = extractedData ? await getAchievementsFromExtractedData(extractedData) : { achievements: [], used_block: null };
  const achievements = achievementsResult.achievements;
  if (achievementsResult.used_block !== null) usedBlockSet.add(achievementsResult.used_block);

// Assuming usedBlockSet is a Set containing block numbers already used
const otherInfo = extractedData
  ? await getExtraFromExtractedData(extractedData, usedBlockSet)
  : {};


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
    otherInfo: otherInfo
  };

  // Delete file after processing
  // fs.unlink(filePath, (err) => {
  //   if (err) console.error('⚠️ Failed to delete file:', err.message);
  // });

  return parsedData;
}

module.exports = parseResume;

// // server.js
// const express = require("express");
// const multer = require("multer");
// const path = require("path");
// const fs = require("fs");
// const parseResume = require("./parser"); // Import your parsing logic

// const app = express();
// const port = 3000;

// // Serve index.html at root
// app.get("/", (req, res) => {
//   res.sendFile(path.join(__dirname, "index.html"));
// });

// // Configure multer for file uploads
// const upload = multer({
//   dest: "uploads/",
//   limits: { fileSize: 5 * 1024 * 1024 }, // limit to 5MB
//   fileFilter: (req, file, cb) => {
//     const ext = path.extname(file.originalname).toLowerCase();
//     if (ext === ".pdf") cb(null, true);
//     else cb(new Error("Only PDF files are allowed."));
//   },
// });

// // API route to upload and parse resume
// app.post("/upload", upload.single("resume"), async (req, res) => {
//   try {
//     const filePath = req.file.path;
//     const parsedData = await parseResume(filePath); // Call your parsing function
//     res.json({ success: true, data: parsedData });
//   } catch (err) {
//     res.status(500).json({ success: false, message: err.message });
//   }
// });

// app.listen(port, () => {
//   console.log(`Server running on http://localhost:${port}`);
// });

const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const { v4: uuidv4 } = require("uuid");
const AdmZip = require("adm-zip");
const parseResume = require("./parser");

const app = express();
const port = 3000;
const uploadDir = path.join(__dirname, "uploads");

if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);

app.use("/uploads", express.static("uploads"));
app.use(express.static(path.join(__dirname, "public")));

let latestResults = []; // store parsed results for display

// Serve index.html
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// Serve results.html
app.get("/results", (req, res) => {
  res.sendFile(path.join(__dirname,"public", "results.html"));
});

// Serve results data for frontend
app.get("/parsed-results", (req, res) => {
  res.json({ results: latestResults });
});

// Bulk handler
const upload = multer().fields([
  { name: "files", maxCount: 20 },
  { name: "zip", maxCount: 1 }
]);

app.post("/upload-resumes", upload, async (req, res) => {
  const pdfBuffers = [];

  if (req.files.files) {
    for (const file of req.files.files) {
      pdfBuffers.push({ buffer: file.buffer, originalname: file.originalname });
    }
  }

  if (req.files.zip) {
    const zip = new AdmZip(req.files.zip[0].buffer);
    const zipEntries = zip.getEntries();

    for (const entry of zipEntries) {
      if (entry.entryName.toLowerCase().endsWith(".pdf")) {
        pdfBuffers.push({ buffer: entry.getData(), originalname: entry.entryName });
      }
    }
  }

  const results = [];
  for (const pdf of pdfBuffers) {
    const filename = `${uuidv4()}.pdf`;
    const filepath = path.join(uploadDir, filename);

    fs.writeFileSync(filepath, pdf.buffer);
    try {
      const parsed = await parseResume(filepath);
      results.push({ filename: pdf.originalname, storedName: filename, data: parsed });
    } catch (err) {
      results.push({ filename: pdf.originalname, storedName: filename, data: { error: err.message } });
    }
  }

  latestResults = results;
  res.redirect("/results");
});

app.listen(port, () => {
  console.log(`✅ Server running at http://localhost:${port}`);
});
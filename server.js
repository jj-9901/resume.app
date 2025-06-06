
// server.js
const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const parseResume = require("./parser"); // Import your parsing logic

const app = express();
const port = 3000;

// Serve index.html at root
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// Configure multer for file uploads
const upload = multer({
  dest: "uploads/",
  limits: { fileSize: 5 * 1024 * 1024 }, // limit to 5MB
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (ext === ".pdf") cb(null, true);
    else cb(new Error("Only PDF files are allowed."));
  },
});

// API route to upload and parse resume
app.post("/upload", upload.single("resume"), async (req, res) => {
  try {
    const filePath = req.file.path;
    const parsedData = await parseResume(filePath); // Call your parsing function
    res.json({ success: true, data: parsedData });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});

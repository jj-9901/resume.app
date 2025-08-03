
// // // server.js
// // const express = require("express");
// // const multer = require("multer");
// // const path = require("path");
// // const fs = require("fs");
// // const parseResume = require("./parser"); // Import your parsing logic

// // const app = express();
// // const port = 3000;

// // // Serve index.html at root
// // app.get("/", (req, res) => {
// //   res.sendFile(path.join(__dirname, "index.html"));
// // });

// // // Configure multer for file uploads
// // const upload = multer({
// //   dest: "uploads/",
// //   limits: { fileSize: 5 * 1024 * 1024 }, // limit to 5MB
// //   fileFilter: (req, file, cb) => {
// //     const ext = path.extname(file.originalname).toLowerCase();
// //     if (ext === ".pdf") cb(null, true);
// //     else cb(new Error("Only PDF files are allowed."));
// //   },
// // });

// // // API route to upload and parse resume
// // app.post("/upload", upload.single("resume"), async (req, res) => {
// //   try {
// //     const filePath = req.file.path;
// //     const parsedData = await parseResume(filePath); // Call your parsing function
// //     res.json({ success: true, data: parsedData });
// //   } catch (err) {
// //     res.status(500).json({ success: false, message: err.message });
// //   }
// // });

// // app.listen(port, () => {
// //   console.log(`Server running on http://localhost:${port}`);
// // });








const express = require("express");
const multer = require("multer");
const path = require("path");
const fs = require("fs");
const { v4: uuidv4 } = require("uuid");
const AdmZip = require("adm-zip");
const parseResume = require("./parser");
const convertDocToPdf = require("./utils/convertToPdf"); // you'll create this next


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

  // if (req.files.files) {
  //   for (const file of req.files.files) {
  //     pdfBuffers.push({ buffer: file.buffer, originalname: file.originalname });
  //   }
  // }


  if (req.files.files) {
  for (const file of req.files.files) {
    const ext = path.extname(file.originalname).toLowerCase();

    if (ext === ".pdf") {
      pdfBuffers.push({ buffer: file.buffer, originalname: file.originalname });
    } else if (ext === ".doc" || ext === ".docx") {
      try {
        const converted = await convertDocToPdf(file.buffer);
        pdfBuffers.push({ buffer: converted, originalname: file.originalname });
      } catch (err) {
        latestResults.push({
          filename: file.originalname,
          storedName: null,
          data: { error: "Conversion failed: " + err.message },
        });
      }
    }
  }
}


  // if (req.files.zip) {
  //   const zip = new AdmZip(req.files.zip[0].buffer);
  //   const zipEntries = zip.getEntries();

  //   for (const entry of zipEntries) {
  //     if (entry.entryName.toLowerCase().endsWith(".pdf")) {
  //       pdfBuffers.push({ buffer: entry.getData(), originalname: entry.entryName });
  //     }
  //   }
  // }

  if (req.files.zip) {
  const zip = new AdmZip(req.files.zip[0].buffer);
  const zipEntries = zip.getEntries();

  for (const entry of zipEntries) {
    if (entry.isDirectory) continue; // skip folders

    const ext = path.extname(entry.entryName).toLowerCase();
    const buffer = entry.getData();

    if (ext === ".pdf") {
      pdfBuffers.push({ buffer, originalname: entry.entryName });
    } else if (ext === ".doc" || ext === ".docx") {
      try {
        const converted = await convertDocToPdf(buffer);
        pdfBuffers.push({ buffer: converted, originalname: entry.entryName });
      } catch (err) {
        latestResults.push({
          filename: entry.entryName,
          storedName: null,
          data: { error: "Conversion failed: " + err.message },
        });
      }
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






// const express = require("express");
// const multer = require("multer");
// const path = require("path");
// const fs = require("fs");
// const { v4: uuidv4 } = require("uuid");
// const AdmZip = require("adm-zip");
// const parseResume = require("./parser");
// const convertDocToPdf = require("./utils/convertToPdf");

// const app = express();
// const port = 3000;
// const uploadDir = path.join(__dirname, "uploads");

// if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);

// app.use("/uploads", express.static("uploads"));
// app.use(express.static(path.join(__dirname, "public")));

// let latestResults = [];

// app.get("/", (req, res) => {
//   res.sendFile(path.join(__dirname, "index.html"));
// });

// app.get("/results", (req, res) => {
//   res.sendFile(path.join(__dirname, "public", "results.html"));
// });

// app.get("/parsed-results", (req, res) => {
//   res.json({ results: latestResults });
// });

// const upload = multer().fields([
//   { name: "files", maxCount: 20 },
//   { name: "zip", maxCount: 1 },
// ]);

// app.post("/upload-resumes", upload, async (req, res) => {
//   const pdfBuffers = [];
//   latestResults = []; // clear old results

//   // Handle individual uploaded files
//   if (req.files?.files) {
//     for (const file of req.files.files) {
//       const ext = path.extname(file.originalname).toLowerCase();
//       try {
//         if (ext === ".pdf") {
//           pdfBuffers.push({ buffer: file.buffer, originalname: file.originalname });
//         } else if (ext === ".doc" || ext === ".docx") {
//           const converted = await convertDocToPdf(file.buffer);
//           pdfBuffers.push({ buffer: converted, originalname: file.originalname });
//         } else {
//           latestResults.push({
//             filename: file.originalname,
//             storedName: null,
//             data: { error: "Unsupported file type" },
//           });
//         }
//       } catch (err) {
//         latestResults.push({
//           filename: file.originalname,
//           storedName: null,
//           data: { error: "Conversion failed: " + err.message },
//         });
//       }
//     }
//   }

//   // Handle ZIP file
//   if (req.files?.zip) {
//     const zip = new AdmZip(req.files.zip[0].buffer);
//     const zipEntries = zip.getEntries();

//     for (const entry of zipEntries) {
//       if (entry.isDirectory) continue;

//       const ext = path.extname(entry.entryName).toLowerCase();
//       const buffer = entry.getData();
//       try {
//         if (ext === ".pdf") {
//           pdfBuffers.push({ buffer, originalname: entry.entryName });
//         } else if (ext === ".doc" || ext === ".docx") {
//           const converted = await convertDocToPdf(buffer);
//           pdfBuffers.push({ buffer: converted, originalname: entry.entryName });
//         } else {
//           latestResults.push({
//             filename: entry.entryName,
//             storedName: null,
//             data: { error: "Unsupported file type in zip" },
//           });
//         }
//       } catch (err) {
//         latestResults.push({
//           filename: entry.entryName,
//           storedName: null,
//           data: { error: "Conversion failed: " + err.message },
//         });
//       }
//     }
//   }

//   // Parse all collected PDFs
//   for (const pdf of pdfBuffers) {
//     const filename = `${uuidv4()}.pdf`;
//     const filepath = path.join(uploadDir, filename);

//     fs.writeFileSync(filepath, pdf.buffer);
//     try {
//       const parsed = await parseResume(filepath);
//       latestResults.push({
//         filename: pdf.originalname,
//         storedName: filename,
//         data: parsed || { error: "Parsed result is empty" },
//       });
//     } catch (err) {
//       latestResults.push({
//         filename: pdf.originalname,
//         storedName: filename,
//         data: { error: "Parsing failed: " + err.message },
//       });
//     }
//   }

//   res.redirect("/results");
// });

// app.listen(port, () => {
//   console.log(`✅ Server running at http://localhost:${port}`);
// });

const libre = require("libreoffice-convert");

function convertDocToPdf(buffer) {
  return new Promise((resolve, reject) => {
    libre.convert(buffer, ".pdf", undefined, (err, done) => {
      if (err) reject(err);
      else resolve(done);
    });
  });
}

module.exports = convertDocToPdf;

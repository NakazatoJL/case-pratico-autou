const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const pdf = require('pdf-parse')

const jobs = {}; // armazenamento em memoria

function createJob(input, API, messageID) {
  const id = uuidv4();
  jobs[id] = { status: 'pending', input, messageID, results: null, error: null };

  // Inicia processo asincrono
  processJob(id, API);

  return id;
}

async function processJob(id, API) {
  try {
    const input = jobs[id].input;
    
    console.log(input);
    // Chama a API em Python para pre processar a mensagem e fazer chamada a API OpenAI
    const response = await axios.post(`${API}/processText`, {
      message: input,
      timeout:10000
    });

    // store the API response
    jobs[id].results = response.data; //Data recebida contem uma lista com "original_text","classification","processed_text","suggestion"
    console.log("Suggestion received: " + jobs[id].results.results[0].suggestion);
    jobs[id].status = 'done';
  } catch (error) {
    // Log the specific error code, message, and stack trace
    console.error('FastAPI call failed!');
    
    // For Axios, log the status and response body if available
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    } else if (error.request) {
      // Request was made but no response received (likely a timeout or DNS/Network issue)
      console.error('No response received (Network/Timeout issue).');
      console.error('Error code:', error.code); // Look for 'ECONNREFUSED' or 'ETIMEDOUT'
    } else {
      // Something happened in setting up the request
      console.error('Request setup error:', error.message);
    }
  }
}

function getJob(id) {
  return jobs[id] || null;
}

// Helper to convert file buffer to string
async function getFileContentAsString(buffer, mimeType) {
  if (mimeType === 'text/plain') {
    return buffer.toString('utf8');
  } else if (mimeType === 'application/pdf') {
    try {
      const data = await pdf(buffer);
      return data.text.trim();
    } catch (error) {
      console.error('Error parsing PDF:', error);
      return `[PDF PARSE ERROR: ${error.message}]`;
    }
  } else {
    return `[UNSUPPORTED FILE TYPE: ${mimeType}]`;
  }
}

module.exports = { createJob, getJob, getFileContentAsString};

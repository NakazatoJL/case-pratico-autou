require('dotenv').config();
const fileUpload = require('express-fileupload');
const express = require('express');
const path = require('path');
const { createJob, getJob,getFileContentAsString} = require('./jobs');

const app = express();

const PORT = 8080;
const FAST_API = process.env.FAST_API;

app.use(fileUpload({
  useTempFiles: false,                 // keep files in memory
  limits: { fileSize: 10 * 1024 * 1024, // 10MB per file
            files:5 // Maximum 10 files per request
          } 
}));

// Arquivos estaticos
app.use(express.static(path.join(__dirname, 'public')));
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');

// Cria armazenamento em memoria para as mensagens
let messages = [];

// Declara a classe para mensagem
class Message {
  constructor(author, content, id) {
    this.id = id || messages.length;
    this.author = author;
    this.content = content;
  }
}

// Caminho para processar as mensagens do usuario
app.post('/message', async (req, res) => {
  let finalContentList = [];
  let filesNames = '<br>';

  try {
    console.log('--- Received Form Data for /message ---');

    const author = req.body.fAuthor;
    const content = req.body.fContent || '';
    if (content.trim()) finalContentList.push(content);

    // Verifica a existencia de arquivos
    const uploaded = req.files?.fUploadedFiles;
    const files = Array.isArray(uploaded) ? uploaded : uploaded ? [uploaded] : [];
    
    // Processa nossos arquivos transformando em texto
    for (const file of files) {
      console.log(`Processing file: ${file.name} (${file.mimetype})`);
      filesNames += `${file.name}<br>`; // Armazena os nomes dos arquivos para envier na mensagem de retorno para o usuario
      const fileString = await getFileContentAsString(file.data, file.mimetype);
      finalContentList.push(fileString);
    }

    console.log('--- Processing Complete ---');
    console.log(`Total items in list: ${finalContentList.length}`);

    let newMessageContent;

    if(filesNames != '<br>' && content.trim()){
      filesNames = '<br><br>Arquivos:<br>' + filesNames;
      newMessageContent = content.trim() + filesNames;
    }
    else if(filesNames != '<br>'){
      filesNames = 'Arquivos:<br>' + filesNames;
      newMessageContent = filesNames;
    }
    else{
      newMessageContent = content.trim();
    }

    // Gera mensagem com as informações do request para a interface do usuario
    var newMessage = new Message(author, newMessageContent);
    messages.push(newMessage);

    // Gera mensagem de inicio do processamento da aplicação (gera um id para editar com retorno final)
    var processMessage = new Message("server", "");

    // Cria um novo job para ser processado pela nossa API em python (que fara o NLP, classficação e integrara com a Gemini API para receber sugestão de resposta)
    jobid = createJob(finalContentList, FAST_API, processMessage.id);
    // Altera o conteudo da mensagem de processamento para mostrar o # do job sendo processado
    processMessage.content = `Processando pedido #${jobid}`;
    messages.push(processMessage);

    

    res.status(200).json({
      success: true,
      jobId: jobid,
      message: 'Content successfully processed.',
      count: finalContentList.length
    });

  } catch (error) {
    console.error('SERVER ERROR during file processing:', error);
    res.status(500).json({ error: 'Failed to process files.', details: error.message });
  }
});

app.get("/", (req, res) => {
  if (messages.length > 0) {
    res.render("index.ejs", { messages });
  } else {
    res.render("index.ejs");
  }
});

app.get("/about", (req, res) => {
  res.render("./about.ejs");
});

app.get("/instructions", (req, res) => {
  res.render("./instructions.ejs");
});

app.get("/contact", (req, res) => {
  res.render("./contact.ejs");
});

app.get("/status/:id", (req, res) => {
  const job = getJob(req.params.id);
  res.render("./index.ejs");
});

app.get("/job/:id", (req, res) => {
  const jobId = req.params.id;
  const job = getJob(jobId);
  
  if(!job){
    return res.status(404).json({ error: 'Job ID not found.' });
  }

  if(job.status == 'done'){
      //Updates the message related to the job
      let newMessageContent = "<b>Seguem os resultados do pedido:</b><br>";
      for (const result of job.results.results) {
        newMessageContent += `<br>${result.original_text}<br>`
        newMessageContent += `<br>Classificado como: <b>${result.classification}</b><br>`
        newMessageContent += `<br>Sugiro como resposta:<br><br>${result.suggestion}<br>`
      }
      messages[job.messageID].content = newMessageContent;
      console.log('job is done');
  }
  res.json(job);
});

console.log(`\nStarting local server on port:${PORT}...`);
app.listen(PORT, () => {
    console.log(`✅ Express server listening at http://localhost:${PORT}`);
});
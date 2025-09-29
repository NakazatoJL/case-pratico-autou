const filter = $(".filter");
for (let i = 0; i < filter.length; i++) {
    filter[i].addEventListener('click', function(){
        console.log('filter clicked');
        $(".pop").toggleClass("hidden");
    });
}

$(".navToggle").click(function(){
    console.log('toggle');
    $(".navItem.h").toggleClass("hidden");
    $(".navList").toggleClass("hiddden");
});

$(".navToggle2").click(function(){
    console.log('toggle');
    $(".navItem.h").toggleClass("hidden");
    $(".navList").toggleClass("hiddden");
});

// Script para verificar o tamanho da janela, ajustando a barra de navegação quando ela for maior ou menor que 600px (valor que atende bem celulares e tablets menores)
function checkWindowSize(){
    if(window.innerWidth <= 600){
        $(".navItem.h").addClass("hidden");
        $(".navToggle").removeClass("hidden");
    }
    else{
        $(".navItem.h").removeClass("hidden");
        $(".navToggle").addClass("hidden");
        $(".navToggle2").addClass("hidden");
    }
}

// Checagem inicial
checkWindowSize();

// Checar quando a janela mudar de tamanho
$(window).on("resize", function(){
    checkWindowSize();
});

// Variável global para o timer
let pollTimer = null; 
const POLL_INTERVAL = 2000; // 2 segundos

// Função para iniciar o monitoramento de job
function startPollingFromStorage() {
    const jobId = localStorage.getItem('currentJobId');
    
    if (jobId) {
        // Opcional: Limpa imediatamente o storage para evitar que o polling reinicie 
        // em futuros reloads não relacionados ao job (ex: se o usuário apertar F5)
        localStorage.removeItem('currentJobId');
        
        // Por exemplo, você pode usar o jobId para atualizar um elemento:
        // document.getElementById('status-box').innerText = `Monitorando Job: ${jobId}`;

        console.log(`Página recarregada. Iniciando monitoramento para Job ID: ${jobId}`);

        // Inicia o Polling
        pollTimer = setInterval(() => checkJobStatus(jobId), POLL_INTERVAL);
        
        // (A função checkJobStatus precisa limpar o pollTimer)

    }
}

// Função de Polling: verifica o status repetidamente
async function checkJobStatus(jobId) {

    const submit = $('#messageSubmit');
    const text = $('#buttonLabel');
    submit.prop('disabled', true)
    text.addClass("hidden");

    try {
        const response = await fetch(`/job/${jobId}`);
        if (!response.ok) throw new Error('Falha ao verificar status do job.');
            
        const jobData = await response.json();
        const status = jobData.status;


        if (status === 'done') {
            // PARAR O POLLING
            clearInterval(pollTimer);
            pollTimer = null; // Zera a variável global
            localStorage.removeItem('currentJobId'); 
            submit.prop('disabled', false)
            text.removeClass("hidden");
            // Recarrega a página em caso de sucesso
            window.location.reload();
        } else if (status === 'processing') {
            // Continua o polling
        }
                
    } catch (error) {
        console.error('Erro no Polling:', error);
        clearInterval(pollTimer);
        pollTimer = null; // Zera a variável em caso de erro
        localStorage.removeItem('currentJobId'); 
        submit.prop('disabled', false)
        text.removeClass("hidden");
    }
}

// Espera o documento carregar
$(document).ready(function() {
    const messageForm = $('.messageForm');
    const messageArea = $('#messageArea');
    const fileInput = $('#documentFiles');
    const fileCount = $('#fileCount');

    maxLenght = 10;
    maxFileSize = 10 * 1024 * 1024;

    // Adiciona event listener ao formulario
    messageForm.on('submit', function(e) {
        // Previne o envio padrão do formulario
        e.preventDefault();

        // Mostra um indicador de processamento simples (modifica o botão e seu texto)
        const submitButton = messageForm.find('#messageSubmit');
        const buttonText = $('#buttonLabel');
        submitButton.prop('disabled', true)
        buttonText.addClass("hidden");
        
        // Inicia o objeto de formulario vazio
        const formData = new FormData();

        // Garante que o autor sempre esta presente
        formData.append('fAuthor', messageForm.find('input[name="fAuthor"]').val());

        // Gera uma boolean para a existencia ou não de texto/arquivo
        const hasText = !!messageArea.val().trim();
        const hasFiles = fileInput[0].files.length > 0;

        if(hasText)
        {
            formData.append('fContent', messageArea.val());
        }

        // CRITICAL CHECK: Garante que existem arquivos ou mensagem antes de enviar
        if (!hasText && !hasFiles) {
            // Mostra mensagem de alerta caso nenhum arquivo ou texto seja enviado (usuario clica no botão sem preencher o formulario)
            alert("Envie pelo menos uma das opções (arquivo ou texto)!");
            submitButton.prop('disabled', false)
            buttonText.removeClass("hidden");
            return;
        }

        // Adiciona arquivos apenas se eles existirem
        if (hasFiles) {
            // Verifica se o numero de arquivos excede o valor maximo
            if(fileInput[0].files.length > maxLenght){ 
                alert("Envie menos de 10 arquivos!");
                submitButton.prop('disabled', false)
                buttonText.removeClass("hidden");
                return;
            }
            // Verifica se algum arquivo possui mais de 10MB
            for (let i = 0; i < fileInput[0].files.length; i++) {
                if(fileInput[0].files[i].size > maxFileSize){
                    alert("Arquivo excede o limite de 10MB!");
                    submitButton.prop('disabled', false)
                    buttonText.removeClass("hidden");
                    return;
                }
            }
            // Faz um loop entre os arquivos e os adiciona a chave correta
            for (let i = 0; i < fileInput[0].files.length; i++) {
                formData.append('fUploadedFiles', fileInput[0].files[i]);
            }
        }
        
        // Logica de envio
        const targetUrl = messageForm.attr('action');

        fetch(targetUrl, {
            method: 'POST',
            body: formData 
        })
        .then(response => {
            submitButton.prop('disabled', false)
            buttonText.removeClass("hidden");

            if (!response.ok) {
                return response.json().then(err => {
                alert(`Error: ${err.error}`);
                throw new Error(err.error);
                });
            }

            return response.json();
        })
        .then(data => {
            const jobId = data.jobId;
            console.log(jobId);

            localStorage.setItem('currentJobId', jobId);
            window.location.reload();
        })
        .catch(error => {
            console.error('AJAX Submission Error:', error);
            submitButton.prop('disabled', false)
            buttonText.removeClass("hidden");
            
            // Mostra caixa de alerta com a mensagem 'Erro'
            alert("Erro");
        });
    });

    // Adiciona event listener ao anexador de arquivos
    fileInput[0].addEventListener('change', ()=>{
        if(fileInput[0].files.length === 0){
            fileCount[0].textContent = 'Nenhum arquivo selecionado';
        }else if(fileInput[0].files.length ===1){
            if(fileInput[0].files[0].name.length<15){fileCount[0].textContent = fileInput[0].files[0].name}else{fileCount[0].textContent = fileInput[0].files[0].name.slice(0,15) +'...'}
        }else{
            fileCount[0].textContent = `${fileInput[0].files.length} arquivos selecionados`;
        }
    });

    // Inicia o polling para gerenciamento do job
    startPollingFromStorage();
});

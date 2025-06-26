// Get references to all HTML elements
const promptInput = document.getElementById('prompt-input');
const generateBtn = document.getElementById('generate-btn');
const statusText = document.getElementById('status-text');
const codeDisplay = document.getElementById('code-display');
const videoDisplay = document.getElementById('video-display');
const copyBtn = document.getElementById('copy-btn');
const themeCheckbox = document.getElementById('theme-checkbox');
const darkThemeStyle = document.getElementById('dark-theme-style');
const lightThemeStyle = document.getElementById('light-theme-style');

// --- THEME SWITCHING LOGIC ---
const setTheme = (theme) => {
    localStorage.setItem('theme', theme);
    
    if (theme === 'light') {
        document.body.classList.add('light-mode');
        themeCheckbox.checked = true;
        lightThemeStyle.disabled = false;
        darkThemeStyle.disabled = true;
    } else {
        document.body.classList.remove('light-mode');
        themeCheckbox.checked = false;
        lightThemeStyle.disabled = true;
        darkThemeStyle.disabled = false;
    }
};

themeCheckbox.addEventListener('change', () => {
    if (themeCheckbox.checked) {
        setTheme('light');
    } else {
        setTheme('dark');
    }
});

// On page load, only apply the theme. No need to initialize highlight.js here.
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
});


// --- GENERATION LOGIC ---
const logStatus = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    statusText.innerHTML += `\n[${timestamp}] ${message}`;
    statusText.parentElement.scrollTop = statusText.parentElement.scrollHeight;
};

generateBtn.addEventListener('click', async () => {
    const prompt = promptInput.value;
    if (!prompt) {
        logStatus("ERROR :: Please enter a prompt directive.");
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = "EXECUTING...";
    statusText.textContent = '> STANDBY';
    logStatus(`INITIATING DIRECTIVE...`);
    logStatus(`PROMPT: "${prompt}"`);

    codeDisplay.innerHTML = ''; // Clear previous content
    videoDisplay.innerHTML = '';

    try {
        logStatus("Contacting Generation Matrix (AI)...");
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: prompt })
        });

        logStatus("AI response received. Dispatching to rendering engine...");

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Unknown server error');
        }

        const data = await response.json();

        logStatus("RENDERING COMPLETE. VISUALS ONLINE.");
        
        // --- THIS IS THE NEW, ROBUST HIGHLIGHTING METHOD ---
        // 1. Manually highlight the raw code string for the 'python' language.
        const highlightedCode = hljs.highlight(data.generated_code, { language: 'python' }).value;
        // 2. Set the innerHTML of our code block to the result.
        codeDisplay.innerHTML = highlightedCode;
        // ----------------------------------------------------
        
        const videoElement = document.createElement('video');
        videoElement.src = data.video_url;
        videoElement.controls = true;
        videoElement.autoplay = true;
        videoElement.muted = true;
        videoDisplay.appendChild(videoElement);

    } catch (error) {
        logStatus(`CRITICAL ERROR :: ${error.message}`);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "EXECUTE";
        logStatus("> AWAITING NEW DIRECTIVE...");
    }
});

// Copy button logic
copyBtn.addEventListener('click', () => {
    // We now use .innerText to copy the code without HTML tags
    const code = codeDisplay.innerText; 
    navigator.clipboard.writeText(code).then(() => {
        copyBtn.textContent = "COPIED";
        setTimeout(() => { copyBtn.textContent = "COPY"; }, 2000);
    }).catch(err => {
        console.error('Failed to copy code: ', err);
    });
});
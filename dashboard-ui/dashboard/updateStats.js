/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const VM_URL = "VM_URL_PLACEHOLDER";
const PROCESSING_STATS_API_URL = `http://${VM_URL}/processing/stats`;
const CHECK_API_URL = `http://${VM_URL}/consistency_check/checks`;
const UPDATE_API_URL = `http://${VM_URL}/consistency_check/update`;

const getRandomIndex = () => Math.floor(Math.random() * 10);
const ANALYZER_API_URL = {
    stats: `http://${VM_URL}/analyzer/stats`,
    chat: `http://${VM_URL}/analyzer/stream/chats?index=${getRandomIndex()}`,
    donation: `http://${VM_URL}/analyzer/stream/donations?index=${getRandomIndex()}`
}

// This function fetches and updates the general statistics
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            updateErrorMessages(error.message)
        })
}

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result)

const getLocaleDateStr = () => (new Date()).toLocaleString()

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats"))
    makeReq(ANALYZER_API_URL.chat, (result) => updateCodeDiv(result, "event-chat"))
    makeReq(ANALYZER_API_URL.donation, (result) => updateCodeDiv(result, "event-donation"))
    makeReq(CHECK_API_URL, (result) => updateCodeDiv(result, "check"))
}

const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, 7000)
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), 4000) // Update every 4 seconds
}

document.addEventListener('DOMContentLoaded', setup)
document.getElementById("update").addEventListener("click", () => {
    fetch(UPDATE_API_URL, { method: "POST" })
        .then(response => response.json())
        .then(data => console.log("Update successful:", data))
        .catch(error => console.error("Error updating:", error));
});
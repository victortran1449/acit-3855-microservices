/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const VM_URL = "VM_URL_PLACEHOLDER"
const PROCESSING_STATS_API_URL = `http://${VM_URL}:8100/stats`

const getRandomIndex = () => Math.floor(Math.random() * 10);
const ANALYZER_API_URL = {
    stats: `http://${VM_URL}:8110/stats`,
    chat: `http://${VM_URL}:8110/stream/chats?index=${getRandomIndex()}`,
    donation: `http://${VM_URL}:8110/stream/donations?index=${getRandomIndex()}`
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
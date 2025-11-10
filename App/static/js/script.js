// script.js — UI helpers, small niceties

// show an unobtrusive toast (uses Bootstrap's toast element creation)
function showToast(message, type='info', timeout=3500){
  const toastContainer = document.getElementById('toastContainer') || (function(){
    const el = document.createElement('div'); el.id='toastContainer';
    el.className='position-fixed top-0 end-0 p-3'; el.style.zIndex=1050;
    document.body.appendChild(el); return el;
  })();

  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${type==='success'?'success':type==='error'?'danger':'light'} border-0 show`;
  toast.role = "alert";
  toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div>
    <button type="button" class="btn-close btn-close-white ms-2 me-2" data-bs-dismiss="toast"></button></div>`;
  toastContainer.appendChild(toast);
  setTimeout(()=>{ toast.classList.remove('show'); toast.remove(); }, timeout);
}

// convenience fetch wrapper to show loading states for buttons
async function postForm(url, data, btn=null){
  try {
    if(btn){ btn.disabled=true; btn.dataset.orig = btn.innerHTML; btn.innerHTML = 'Processing…'; }
    const res = await fetch(url, { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams(data) });
    const json = await res.json();
    if(btn){ btn.disabled=false; btn.innerHTML = btn.dataset.orig; }
    return json;
  } catch(err){
    if(btn){ btn.disabled=false; btn.innerHTML = btn.dataset.orig; }
    showToast('Network error', 'error');
    throw err;
  }
}

// add a little animation to links
document.querySelectorAll('a').forEach(link => {
  if (!link.classList.contains('btn') && !link.classList.contains('nav-link')) {
    link.style.transition = 'color 0.2s ease';
  }
});

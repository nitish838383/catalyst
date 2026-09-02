
window.Auth={
 save(token){localStorage.setItem('skillbridge_token',token)},clear(){localStorage.removeItem('skillbridge_token');localStorage.removeItem('skillbridge_user')},
 async me(force=false){if(!force){const c=localStorage.getItem('skillbridge_user');if(c){try{return JSON.parse(c)}catch{}}} const me=await SB.get('/users/me'); localStorage.setItem('skillbridge_user',JSON.stringify(me)); return me},
 home(role){return role==='student'?'/student/dashboard.html':role==='recruiter'?'/recruiter/dashboard.html':role==='college'?'/college/dashboard.html':role==='admin'?'/admin/dashboard.html':'/'},
 async guard(role){if(!SB.token()){location.href='/login.html';return null}try{const me=await this.me(true);if(role&&me.role!==role){location.href=this.home(me.role);return null}return me}catch(e){this.clear();location.href='/login.html';return null}},
 logout(){this.clear();location.href='/login.html'}
};

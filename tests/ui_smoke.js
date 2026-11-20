// Small Node smoke test for the unchanged Tabler-rendering UI and SQLite adapter.
// No browser or dependencies required; DOM elements are minimal mocks.
const fs=require('fs'); const vm=require('vm');
const payload=JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const elements=new Map();
function fake(){return {innerHTML:'',scrollTop:0, classList:{add(){},remove(){},toggle(){}},
  setAttribute(){},focus(){},setSelectionRange(){},selectionStart:0};}
const handlers={};
const document={
 querySelector(q){if(!elements.has(q))elements.set(q,fake());return elements.get(q);},
 documentElement:fake(), addEventListener(type,cb){handlers[type]=cb;}
};
const sessionStorage={values:{},getItem(k){return this.values[k]||null},setItem(k,v){this.values[k]=v}};
const sent=[];
const sandbox={
 document,sessionStorage,console,structuredClone,Math,Date,Number,String,Array,Object,JSON,
 window:{scrollTo(){},clearTimeout(){},setTimeout(){return 1}},
 setTimeout(){return 1},clearTimeout(){},
 fetch:async (url,opts)=>{
   if(url==='/api/bootstrap')return {ok:true,json:async()=>payload};
   if(url==='/api/state'){sent.push(JSON.parse(opts.body));return {ok:true,json:async()=>({ok:true})};}
   return {ok:false,status:404};
 },
 location:{reload(){}},
 FormData: class{constructor(form){this.data=form.values;}get(k){return this.data[k]}},
};
sandbox.window.window=sandbox.window;
vm.runInNewContext(fs.readFileSync('js/app.js','utf8'),sandbox,{filename:'app.js'});
function click(selector,dataset){handlers.click({target:{closest:query=> query===selector ? {dataset}:null}})}
const sleep=()=>new Promise(r=>setTimeout(r,0));
(async()=>{
 await sleep();
 if(!elements.get('#sidebar-nav').innerHTML.includes('Applicant CRM'))throw new Error('Recruiter navigation missing');
 click('[data-role]',{role:'student'});
 if(!elements.get('#sidebar-nav').innerHTML.includes('Smart Recommendations'))throw new Error('Student navigation missing');
 click('[data-action]',{action:'apply:GD310'});
 await sleep();
 const s=sandbox.window.EduPathDemo.state();
 if(!s.applications.some(a=>a.programme==='GD310'&&a.student==='Tariro Moyo'))throw new Error('Application not created');
 click('[data-role]',{role:'recruiter'});
 const form={getAttribute:()=> 'campaign-form',matches:()=>true,values:{name:'QA Local Campaign',channel:'Facebook',budget:'200'}};
 handlers.submit({target:form,preventDefault(){}});
 await sleep();
 const after=sandbox.window.EduPathDemo.state();
 if(!after.campaigns.some(c=>c.name==='QA Local Campaign'))throw new Error('Campaign not created');
 if(sent.length<2)throw new Error('SQLite POST save was not sent');
 console.log('UI smoke PASSED: 2 portals, student apply, new campaign, SQLite state POST');
})().catch(e=>{console.error(e);process.exitCode=1});

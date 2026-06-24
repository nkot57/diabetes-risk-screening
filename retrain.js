#!/usr/bin/env node
/* =====================================================================
   retrain.js — the periodic "update the weights" step.
   Zero dependencies (Node 18+, uses built-in fetch + fs).

   It (1) reads the base cohort CSV, (2) pulls confirmed submissions from
   your private Supabase table (or a local submissions.csv), (3) validates
   and merges them, (4) trains the same logistic-regression model the
   dashboard uses, and (5) writes weights.json — the curated model every
   visitor then loads.

   Usage:
     node retrain.js                          # base CSV only
     node retrain.js submissions.csv          # base CSV + a local export
     SUPABASE_URL=https://xxx.supabase.co \
     SUPABASE_SERVICE_KEY=eyJ... node retrain.js   # base CSV + live DB

   The SERVICE key bypasses row-level security so it can READ all rows.
   Keep it secret — it is NEVER put in the browser/index.html.
   ===================================================================== */
const fs = require('fs');

const BASE_CSV = 'Diabetes Classification 2.csv';
const OUT      = 'weights.json';

/* plausibility ranges — rows outside these are dropped (front-line validation) */
const RANGES = {Age:[0,120],BMI:[8,90],Glucose:[1,50],Chol:[0,20],TG:[0,30],HDL:[0,10],LDL:[0,20],Cr:[5,2000],BUN:[0,100]};

/* ---------- tiny CSV parser (simple numeric data, no quoted commas) ---------- */
function parseCSV(text){
  const lines = text.replace(/\r/g,'').split('\n').filter(l=>l.length);
  const headers = lines[0].split(',');
  return lines.slice(1).map(line=>{
    const cells = line.split(',');
    const o={}; headers.forEach((h,i)=>o[h]=cells[i]); return o;
  });
}
function numericCols(rows, headers){
  return headers.filter(h=>{ if(!h||h==='Diagnosis') return false;
    let ok=0,tot=0; for(const r of rows.slice(0,300)){ if(r[h]===''||r[h]==null) continue; tot++; if(Number.isFinite(Number(r[h]))) ok++; }
    return tot>0 && ok/tot>0.9; });
}
function valid(features, raw){
  for(let j=0;j<features.length;j++){ const rng=RANGES[features[j]]; if(rng && (raw[j]<rng[0]||raw[j]>rng[1])) return false; }
  return true;
}

/* ---------- gather rows ---------- */
function rowsFromObjects(objs, features, srcLabel){
  const X=[],y=[]; let dropped=0;
  for(const r of objs){
    const dRaw = (r.Diagnosis!==undefined)?r.Diagnosis:r.diagnosis;
    const d=Number(dRaw); if(d!==0&&d!==1){dropped++; continue;}
    const row=new Array(features.length); let ok=true;
    for(let j=0;j<features.length;j++){ const key = r[features[j]]!==undefined ? features[j] : features[j].toLowerCase();
      const v=Number(r[key]); if(!Number.isFinite(v)){ok=false;break;} row[j]=v; }
    if(!ok || !valid(features,row)){ dropped++; continue; }
    X.push(row); y.push(d);
  }
  if(dropped) console.log(`  ${srcLabel}: dropped ${dropped} invalid/out-of-range row(s)`);
  return {X,y};
}

async function fetchSubmissions(features){
  const url=process.env.SUPABASE_URL, key=process.env.SUPABASE_SERVICE_KEY;
  if(!url||!key) return {X:[],y:[]};
  const res=await fetch(url+'/rest/v1/submissions?select=*',{headers:{apikey:key,Authorization:'Bearer '+key}});
  if(!res.ok){ console.error('  Supabase read failed:',res.status, await res.text()); return {X:[],y:[]}; }
  const data=await res.json();
  console.log(`  Supabase: ${data.length} submission(s) fetched`);
  return rowsFromObjects(data, features, 'Supabase');
}

/* ---------- logistic regression (identical math to the dashboard) ---------- */
function train(X,y,epochs=500,lr=0.5,l2=0.0005){
  const N=X.length, D=X[0].length, W=new Array(D).fill(0); let b=0;
  const sig=z=>1/(1+Math.exp(-Math.max(-30,Math.min(30,z))));
  for(let e=0;e<epochs;e++){
    const gW=new Array(D).fill(0); let gb=0;
    for(let i=0;i<N;i++){ let z=b; for(let j=0;j<D;j++) z+=W[j]*X[i][j];
      const p=sig(z), d=p-y[i]; for(let j=0;j<D;j++) gW[j]+=d*X[i][j]; gb+=d; }
    for(let j=0;j<D;j++) W[j]-=lr*(gW[j]/N + l2*W[j]); b-=lr*(gb/N);
  }
  return {W,b};
}

(async function(){
  if(!fs.existsSync(BASE_CSV)){ console.error('Missing base CSV:',BASE_CSV); process.exit(1); }
  const base = parseCSV(fs.readFileSync(BASE_CSV,'utf8'));
  const features = numericCols(base, Object.keys(base[0]));
  console.log('Features:', features.join(', '));

  let {X,y} = rowsFromObjects(base, features, 'base');
  console.log(`  base: ${X.length} rows`);

  // local submissions.csv (optional positional arg, defaults to submissions.csv if present)
  const localFile = process.argv[2] || 'submissions.csv';
  if(fs.existsSync(localFile)){
    const s = rowsFromObjects(parseCSV(fs.readFileSync(localFile,'utf8')), features, localFile);
    X=X.concat(s.X); y=y.concat(s.y); console.log(`  ${localFile}: ${s.X.length} rows`);
  }
  // live Supabase
  const sub = await fetchSubmissions(features);
  X=X.concat(sub.X); y=y.concat(sub.y);

  // standardize on the full combined set
  const D=features.length, mean=new Array(D).fill(0), std=new Array(D).fill(0);
  for(const r of X) for(let j=0;j<D;j++) mean[j]+=r[j]; for(let j=0;j<D;j++) mean[j]/=X.length;
  for(const r of X) for(let j=0;j<D;j++){ const d=r[j]-mean[j]; std[j]+=d*d; } for(let j=0;j<D;j++) std[j]=Math.sqrt(std[j]/X.length)||1;
  const Xs = X.map(r=>r.map((v,j)=>(v-mean[j])/std[j]));

  const {W,b} = train(Xs,y);
  const out = {features, mean:mean.map(v=>+v.toFixed(6)), std:std.map(v=>+v.toFixed(6)),
    W:W.map(v=>+v.toFixed(6)), b:+b.toFixed(6), trainedOn:X.length, updated:new Date().toISOString().slice(0,10)};
  fs.writeFileSync(OUT, JSON.stringify(out,null,2));
  console.log(`\nWrote ${OUT}: trained on ${X.length} people across ${features.length} markers.`);
  console.log('Weights:', Object.fromEntries(features.map((f,j)=>[f,out.W[j]])), 'bias', out.b);
  console.log('\nCommit weights.json to publish the updated model to all visitors.');
})();

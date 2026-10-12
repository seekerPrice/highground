"use client";
import {useEffect,useRef,useState} from "react";
import type * as Leaflet from "leaflet";
import "leaflet/dist/leaflet.css";
import type {Dashboard,Level} from "../lib/contracts";
const colors:Record<Level,string>={none:"#17324D",watch:"#9A6700",warning:"#B6481A",danger:"#AF1F39"};
export default function DashboardMap({data,selected,onSelect}:{data:Dashboard;selected:string|null;onSelect:(id:string)=>void}) {
 const host=useRef<HTMLDivElement|null>(null),map=useRef<Leaflet.Map|null>(null),layers=useRef<Leaflet.LayerGroup|null>(null),library=useRef<typeof Leaflet|null>(null);
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);const fitted=useRef(false);
 useEffect(()=>{let alive=true;let observer:ResizeObserver|null=null;
  void import("leaflet").then(L=>{if(!alive||!host.current)return;library.current=L;
   // View centre is the sourced Pasar Moden Sri Muda registry coordinate, not an alert origin.
   const instance=L.map(host.current,{scrollWheelZoom:false,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false}).setView([3.0314414,101.5356055],14);
   map.current=instance;layers.current=L.layerGroup().addTo(instance);
   L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(instance);
   observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(host.current);setReady(true);
  }).catch(()=>{if(alive)setFailed(true);});
  return()=>{alive=false;observer?.disconnect();map.current?.remove();map.current=null;};
 },[]);
 useEffect(()=>{const L=library.current,instance=map.current,group=layers.current;if(!ready||!L||!instance||!group)return;
  group.clearLayers();const points:Leaflet.LatLngTuple[]=[];
  for(const event of data.events){const point:Leaflet.LatLngTuple=[event.lat,event.lng];points.push(point);const circle=L.circle(point,{radius:event.radius_m,color:colors[event.level],weight:2,dashArray:event.level==="danger"?undefined:"6 5",fillOpacity:event.level==="danger"?.17:.035});const label=document.createElement("p");label.textContent=`Simulation ${event.level}: ${event.reason}`;circle.bindPopup(label).addTo(group);}
  for(const shop of data.shops){const point:Leaflet.LatLngTuple=[shop.lat,shop.lng];points.push(point);const icon=L.divIcon({className:"shop-marker",html:`<span class="map-pin level-${shop.level}${selected===shop.shop_id?" selected":""}">${shop.level==="none"?"•":shop.level.slice(0,1).toUpperCase()}</span>`,iconSize:[40,40],iconAnchor:[20,20]});const label=document.createElement("p");label.textContent=`${shop.shop_name} — ${shop.level==="none"?"No alert level recorded":shop.level}`;L.marker(point,{icon,title:shop.shop_name,alt:`Synthetic shop: ${shop.shop_name}`}).bindPopup(label).on("click",()=>onSelect(shop.shop_id)).addTo(group);}
  for(const place of data.destinations){const point:Leaflet.LatLngTuple=[place.lat,place.lng];points.push(point);const kind=place.type==="parking"?"P":place.type==="pps"?"⌂":"△";const icon=L.divIcon({className:"destination-marker",html:`<span class="place-pin ${place.type}">${kind}</span>`,iconSize:[32,32],iconAnchor:[16,16]});const label=document.createElement("p");label.textContent=`${place.name}. ${place.opening_status==="closed"?"Listed closed":"Current opening unconfirmed"}. Route conditions are unverified.`;L.marker(point,{icon,title:place.name,alt:`Listed destination: ${place.name}`}).bindPopup(label).addTo(group);}
  if(!fitted.current&&points.length){instance.fitBounds(L.latLngBounds(points),{padding:[35,35],maxZoom:15});fitted.current=true;}
 },[ready,data,selected,onSelect]);
 return <div className="map-wrap"><div ref={host} className="neighbourhood-map" role="region" aria-label="Taman Sri Muda simulation map"/>{!ready&&<p className="map-loading" role="status">{failed?"Map unavailable. Use the places list below.":"Loading neighbourhood map…"}</p>}<p className="map-caption">Simulation radii show the configured alert area. Destinations are historical listings; current opening and route conditions are unverified.</p></div>;
}

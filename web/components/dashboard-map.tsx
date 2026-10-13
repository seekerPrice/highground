"use client";
import {useEffect,useRef,useState} from "react";
import type * as Leaflet from "leaflet";
import "leaflet/dist/leaflet.css";
import type {Dashboard,Level,WasteResponse} from "../lib/contracts";
import {estimatedQuantity,wasteMap} from "../lib/waste-summary";
const colors:Record<Level,string>={none:"#17324D",watch:"#9A6700",warning:"#B6481A",danger:"#AF1F39"};
export default function DashboardMap({data,waste,selected,onSelect}:{data:Dashboard;waste:WasteResponse|null;selected:string|null;onSelect:(id:string)=>void}) {
 const [cleanup,setCleanup]=useState(false);
 const cleanupLayer=wasteMap(data,waste);
 const host=useRef<HTMLDivElement|null>(null),map=useRef<Leaflet.Map|null>(null),layers=useRef<Leaflet.LayerGroup|null>(null),library=useRef<typeof Leaflet|null>(null);
 const tiles=useRef<Leaflet.TileLayer|null>(null);
 const zoomHost=useRef<HTMLDivElement|null>(null);
 const [tileStatus,setTileStatus]=useState<"loading"|"ready"|"partial"|"failed">("loading");
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);const fitted=useRef(false);
 useEffect(()=>{let alive=true;let observer:ResizeObserver|null=null;
  void import("leaflet").then(L=>{if(!alive||!host.current)return;library.current=L;
   // View centre is the sourced Pasar Moden Sri Muda registry coordinate, not an alert origin.
   const instance=L.map(host.current,{scrollWheelZoom:false,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false}).setView([3.0314414,101.5356055],14);
   // Keep the library-owned controls outside the popup viewport, including on narrow phones.
   const zoom=instance.zoomControl.getContainer();
   if(zoom&&zoomHost.current)zoomHost.current.appendChild(zoom);
   map.current=instance;layers.current=L.layerGroup().addTo(instance);
   let loaded=0,errors=0;
   const tileLayer=L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'});
   tileLayer.on("loading",()=>{loaded=0;errors=0;if(alive)setTileStatus("loading");});
   tileLayer.on("tileload",()=>{loaded+=1;});
   tileLayer.on("tileerror",()=>{errors+=1;});
   tileLayer.on("load",()=>{if(alive)setTileStatus(errors?(loaded?"partial":"failed"):"ready");});
   tiles.current=tileLayer;tileLayer.addTo(instance);
   observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(host.current);setReady(true);
  }).catch(()=>{if(alive)setFailed(true);});
  return()=>{alive=false;observer?.disconnect();map.current?.remove();map.current=null;tiles.current=null;};
 },[]);
 useEffect(()=>{const L=library.current,instance=map.current,group=layers.current;if(!ready||!L||!instance||!group)return;
  // Read actual map focus before replacing layers; never infer focus from selection.
  const active=document.activeElement;const focusedKey=active instanceof HTMLElement&&host.current?.contains(active)?active.closest<HTMLElement>("[data-map-marker]")?.dataset.mapMarker:null;
  const popupKeys=new Set<string>();let popupFocusKey:string|null=null;group.eachLayer(layer=>{if((layer instanceof L.Marker||layer instanceof L.Circle)&&layer.isPopupOpen()){const key=layer.getElement()?.getAttribute("data-map-marker");if(key){popupKeys.add(key);if(active instanceof HTMLElement&&layer.getPopup()?.getElement()?.contains(active))popupFocusKey=key;}}});
  group.clearLayers();const points:Leaflet.LatLngTuple[]=[];const markers=new globalThis.Map<string,Leaflet.Marker|Leaflet.Circle>();
  for(const event of data.events){const point:Leaflet.LatLngTuple=[event.lat,event.lng];points.push(point);const circle=L.circle(point,{radius:event.radius_m,color:colors[event.level],weight:2,dashArray:event.level==="danger"?undefined:"6 5",fillOpacity:event.level==="danger"?.17:.035});const label=document.createElement("p");label.textContent=`Simulation ${event.level}. Base event radius ${event.radius_m} m; effective Warning targeting may differ by shop. ${event.reason}`;circle.bindPopup(label).addTo(group);const key=`event:${event.event_id}`;markers.set(key,circle);circle.getElement()?.setAttribute("data-map-marker",key);}
  for(const shop of data.shops){const cleanupStreet=cleanup?wasteMap(data,waste).pins.find(pin=>pin.shop.shop_id===shop.shop_id)?.street:null;const point:Leaflet.LatLngTuple=[shop.lat,shop.lng];points.push(point);const icon=L.divIcon({className:"shop-marker",html:`<span class="map-pin level-${shop.level}${selected===shop.shop_id?" selected":""}${cleanupStreet?" cleanup-contributor":""}">${shop.level==="none"?"•":shop.level.slice(0,1).toUpperCase()}</span>`,iconSize:[44,44],iconAnchor:[22,22]});const label=document.createElement("p");label.textContent=`${shop.shop_name} — ${shop.level==="none"?"No alert level recorded":shop.level}`;if(cleanupStreet){label.textContent+=`. Cleanup contributor on ${cleanupStreet.street}. Whole-street estimate (shared across ${cleanupStreet.shop_count} shops, not per pin): ${estimatedQuantity(cleanupStreet.est_volume_m3,"m³")}, ${estimatedQuantity(cleanupStreet.est_weight_kg,"kg")}, ${estimatedQuantity(cleanupStreet.estimated_load_equivalents,"load-equivalents")}. ${cleanupStreet.assessed_items} of ${cleanupStreet.baseline_items} items assessed; ${cleanupStreet.unknown_items} unknown; ${cleanupStreet.unknown_volume_items} volume quantities unknown. No collection or safety promise.`;}const marker=L.marker(point,{icon,title:shop.shop_name,alt:`Synthetic shop: ${shop.shop_name}`}).bindPopup(label).on("click",()=>onSelect(shop.shop_id)).addTo(group);const key=`shop:${shop.shop_id}`;markers.set(key,marker);const element=marker.getElement();if(element)element.dataset.mapMarker=key;element?.setAttribute("aria-label",`Synthetic shop ${shop.shop_name}: ${shop.level==="none"?"no alert recorded":shop.level}`);element?.addEventListener("keydown",event=>{if(event.code==="Space"){event.preventDefault();marker.openPopup();onSelect(shop.shop_id);}});}
  for(const place of data.destinations){const point:Leaflet.LatLngTuple=[place.lat,place.lng];points.push(point);const kind=place.type==="parking"?"P":place.type==="pps"?"⌂":"△";const icon=L.divIcon({className:"destination-marker",html:`<span class="place-pin ${place.type}">${kind}</span>`,iconSize:[44,44],iconAnchor:[22,22]});const label=document.createElement("p");label.textContent=`${place.name}. ${place.opening_status==="closed"?"Listed closed":"Current opening unconfirmed"}. Route conditions are unverified.`;const marker=L.marker(point,{icon,title:place.name,alt:`Listed destination: ${place.name}`}).bindPopup(label).addTo(group);const key=`destination:${place.safe_point_id}`;markers.set(key,marker);const element=marker.getElement();if(element)element.dataset.mapMarker=key;element?.setAttribute("aria-label",`Listed ${place.type==="parking"?"parking":place.type==="pps"?"shelter":"higher ground"}: ${place.name}. Current opening ${place.opening_status==="closed"?"listed closed":"unconfirmed"}`);element?.addEventListener("keydown",event=>{if(event.code==="Space"){event.preventDefault();marker.openPopup();}});}
  for(const key of popupKeys)markers.get(key)?.openPopup();
  if(popupFocusKey){const marker=markers.get(popupFocusKey);const close=marker?.getPopup()?.getElement()?.querySelector<HTMLAnchorElement>("a.leaflet-popup-close-button");const element=marker?.getElement();(close??(element instanceof HTMLElement?element:host.current))?.focus({preventScroll:true});}
  else if(focusedKey){const element=markers.get(focusedKey)?.getElement();(element instanceof HTMLElement?element:host.current)?.focus({preventScroll:true});}
  if(!fitted.current&&points.length){instance.fitBounds(L.latLngBounds(points),{padding:[35,35],maxZoom:15});fitted.current=true;}
 },[ready,data,waste,cleanup,selected,onSelect]);
 return <div className="map-wrap"><div className="cleanup-layer-control"><div className="cleanup-layer-toolbar"><button className="button secondary" aria-pressed={cleanup} onClick={()=>setCleanup(value=>!value)}>Estimated cleanup layer {cleanup?"on":"off"}</button><div ref={zoomHost} className="map-zoom-toolbar" role="group" aria-label="Map zoom"/></div>{cleanup&&<div role="status"><p>{cleanupLayer.note}</p><p>{cleanupLayer.pins.length} contributing shop pins. Outlined pins link to whole-street totals, counted once in the cleanup table. Unassigned streets remain table-only. No boundaries or routes are inferred.</p><a href="#waste-summary-title">Read street totals and unknown quantities</a></div>}</div><div ref={host} className="neighbourhood-map" role="region" tabIndex={0} aria-label="Taman Sri Muda simulation map"/>{!ready&&<p className="map-loading" role="status">{failed?"Map unavailable. Use the places list below.":"Loading neighbourhood map…"}</p>} {ready&&tileStatus!=="ready"&&<div className="tile-notice" role="status"><p>{tileStatus==="loading"?"Loading street map…":tileStatus==="partial"?"Some street-map tiles are unavailable. Pins remain visible; use the places list for details.":"Street map unavailable. Pins remain visible; use the places list for details."}</p>{tileStatus!=="loading"&&<button className="button secondary" onClick={()=>tiles.current?.redraw()}>Retry street map</button>}</div>}<p className="map-caption">Circles show base event radii, not universal actual coverage. Nonofficial Warning targeting can differ by shop. Destinations are historical listings; current opening and route conditions are unverified.</p></div>;
}

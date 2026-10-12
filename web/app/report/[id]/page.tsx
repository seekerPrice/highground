import type { Metadata } from "next";
import ReportView from "../../../components/report-view";
export const dynamic="force-dynamic";
export const metadata:Metadata={title:"Private flood loss estimate | HighGround",robots:{index:false,follow:false},referrer:"no-referrer"};
export default async function ReportPage({params}:{params:Promise<{id:string}>}) {
 const {id}=await params;
 return <ReportView id={id}/>;
}

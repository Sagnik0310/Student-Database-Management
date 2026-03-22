import { Card, CardContent, Typography } from "@mui/material";

export default function DashboardCards({students}){

return(

<div style={{display:"flex",gap:"20px",marginBottom:"30px"}}>

<Card sx={{minWidth:200}}>
<CardContent>
<Typography variant="h6">Total Students</Typography>
<Typography variant="h4">{students.length}</Typography>
</CardContent>
</Card>

</div>

);
}
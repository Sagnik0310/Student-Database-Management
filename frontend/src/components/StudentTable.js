import {
Table,TableBody,TableCell,TableHead,TableRow,
Button
} from "@mui/material";

export default function StudentTable({students,onDelete,onEdit}){

return(

<Table>

<TableHead>
<TableRow>

<TableCell>Reg No</TableCell>
<TableCell>Roll No</TableCell>
<TableCell>Name</TableCell>
<TableCell>Age</TableCell>
<TableCell>Branch</TableCell>
<TableCell>Actions</TableCell>

</TableRow>
</TableHead>

<TableBody>

{students.map((s)=>(

<TableRow key={s.reg_no}>

<TableCell>{s.reg_no}</TableCell>
<TableCell>{s.roll_no}</TableCell>
<TableCell>{s.name}</TableCell>
<TableCell>{s.age}</TableCell>
<TableCell>{s.branch}</TableCell>

<TableCell>

<Button onClick={()=>onEdit(s)}>Edit</Button>

<Button color="error"
onClick={()=>onDelete(s.reg_no)}
>
Delete
</Button>

</TableCell>

</TableRow>

))}

</TableBody>

</Table>

);
}
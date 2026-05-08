import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Button
} from "@mui/material";


export default function StudentTable({
  students,
  onDelete,
  onEdit
}) {

  return (

    <>

      {/* DESKTOP TABLE */}
      <div className="table-wrapper">

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

            {students.map((s) => (

              <TableRow key={s.reg_no}>

                <TableCell>{s.reg_no}</TableCell>
                <TableCell>{s.roll_no}</TableCell>
                <TableCell>{s.name}</TableCell>
                <TableCell>{s.age}</TableCell>
                <TableCell>{s.branch}</TableCell>

                <TableCell>

                  <Button
                    onClick={() => onEdit(s)}
                  >
                    Edit
                  </Button>

                  <Button
                    color="error"
                    onClick={() => onDelete(s.reg_no)}
                  >
                    Delete
                  </Button>

                </TableCell>

              </TableRow>

            ))}

          </TableBody>

        </Table>

      </div>


      {/* MOBILE CARDS */}
      <div>

        {students.map((s) => (

          <div
            className="student-card"
            key={s.reg_no}
          >

            <h3>{s.name}</h3>

            <p>
              <strong>Reg No:</strong> {s.reg_no}
            </p>

            <p>
              <strong>Roll No:</strong> {s.roll_no}
            </p>

            <p>
              <strong>Age:</strong> {s.age}
            </p>

            <p>
              <strong>Branch:</strong> {s.branch}
            </p>

            <div className="card-buttons">

              <button
                className="edit-btn"
                onClick={() => onEdit(s)}
              >
                Edit
              </button>

              <button
                className="delete-btn"
                onClick={() => onDelete(s.reg_no)}
              >
                Delete
              </button>

            </div>

          </div>

        ))}

      </div>

    </>
  );
}
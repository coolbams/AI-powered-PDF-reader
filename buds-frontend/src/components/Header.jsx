
const logoImg = "https://images.unsplash.com/photo-1588768987479-bcebeefb8a5c?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"

export default function Header(){
    return(

            <div className="h-16 my-2  items-center  flex">

                <img src="" alt="Logo" className="w-12 h-12 mr-5 rounded-full object-cover bg-amber-50 object-top" id="Logo Avatar" />

                <h1 className="text-amber-50 text-xl max-w-xl truncate mx-2"> Mastering Tmux: Setup, Configuration, and Workflow Optimization </h1>
            </div>
        
    )
}